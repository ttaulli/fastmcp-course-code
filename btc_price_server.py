# btc_price_server.py
from __future__ import annotations

import os
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Dict, Optional

import requests
from fastmcp import FastMCP  # <-- fixed: no 'mcp' import


# -----------------------------
# Data models (structured I/O)
# -----------------------------

@dataclass
class BTCPriceQuote:
    symbol: str                 # e.g., "BTC"
    convert: str                # e.g., "USD"
    price: float                # e.g., 64000.12
    market_cap: Optional[float]
    volume_24h: Optional[float]
    percent_change_1h: Optional[float]
    percent_change_24h: Optional[float]
    percent_change_7d: Optional[float]
    last_updated: str           # ISO-8601 timestamp from API
    fetched_at: str             # ISO-8601 timestamp (this server)
    source: str                 # e.g., "CoinMarketCap"


# -----------------------------
# MCP server initialization
# -----------------------------

mcp_server = FastMCP("BTC Price MCP")


# -----------------------------
# Helpers
# -----------------------------

def _get_api_key() -> str:
    api_key = os.getenv("COINMARKETCAP_API_KEY")
    if not api_key:
        raise RuntimeError(
            "COINMARKETCAP_API_KEY is not set. "
            "Set it in your environment before running this server."
        )
    return api_key


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# -----------------------------
# Tool: get_btc_price
# -----------------------------

@mcp_server.tool(description="Get the current Bitcoin price using CoinMarketCap.")
def get_btc_price(convert: str = "USD") -> Dict:
    """
    Fetch the latest BTC quote from CoinMarketCap.

    Args:
        convert: The fiat or crypto currency to convert into (e.g., "USD", "EUR", "ETH").

    Returns:
        Dict representation of BTCPriceQuote (JSON-serializable).
    """
    convert = convert.upper().strip()
    api_key = _get_api_key()

    url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
    params = {"symbol": "BTC", "convert": convert}
    headers = {
        "X-CMC_PRO_API_KEY": api_key,
        "Accept": "application/json",
        "User-Agent": "btc-price-mcp/1.0",
    }

    try:
        resp = requests.get(url, params=params, headers=headers, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f"HTTP/network error calling CoinMarketCap: {e}") from e

    try:
        payload = resp.json()
    except ValueError as e:
        raise RuntimeError(f"Failed to parse JSON from CoinMarketCap: {e}") from e

    status = payload.get("status", {})
    if status.get("error_code", 0) != 0:
        code = status.get("error_code")
        msg = status.get("error_message", "Unknown API error")
        raise RuntimeError(f"CoinMarketCap API error {code}: {msg}")

    try:
        btc = payload["data"]["BTC"]
        quote = btc["quote"][convert]
        result = BTCPriceQuote(
            symbol=btc.get("symbol", "BTC"),
            convert=convert,
            price=float(quote["price"]),
            market_cap=float(quote["market_cap"]) if "market_cap" in quote else None,
            volume_24h=float(quote["volume_24h"]) if "volume_24h" in quote else None,
            percent_change_1h=float(quote["percent_change_1h"]) if "percent_change_1h" in quote else None,
            percent_change_24h=float(quote["percent_change_24h"]) if "percent_change_24h" in quote else None,
            percent_change_7d=float(quote["percent_change_7d"]) if "percent_change_7d" in quote else None,
            last_updated=quote.get("last_updated", ""),
            fetched_at=_now_iso(),
            source="CoinMarketCap",
        )
    except KeyError as e:
        raise ValueError(f"Expected field missing in API response: {e}") from e

    return asdict(result)


# -----------------------------
# Entrypoint
# -----------------------------

if __name__ == "__main__":
    # Example:
    #   export COINMARKETCAP_API_KEY="your_key_here"
    #   python btc_price_server.py
    mcp_server.run()


