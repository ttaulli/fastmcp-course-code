# btc_price_server.py
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Dict, Any
import os
import time
import requests

from fastmcp import mcp

# =========================
# Config
# =========================
CMC_KEY = os.getenv("COINMARKETCAP_API_KEY")  # <-- set this in your shell
USER_AGENT = "fastmcp-btc/1.0"
TIMEOUT_SECS = 5.0
MAX_RETRIES = 3
BACKOFF_START = 0.5  # seconds


# =========================
# Data model
# =========================
@dataclass
class BTCResult:
    symbol: str       # "BTC"
    currency: str     # "USD", "EUR", etc.
    price: float
    change_24h: float
    volume: float
    as_of: str        # ISO-like timestamp
    source: str       # "coinmarketcap"


# =========================
# Helpers
# =========================
def _http_get(url: str, headers: Dict[str, str], params: Dict[str, str]) -> requests.Response:
    """GET with simple retry/backoff for 429/5xx, plus a hard timeout."""
    backoff = BACKOFF_START
    last_exc: Exception | None = None

    for _ in range(MAX_RETRIES):
        try:
            r = requests.get(url, headers=headers, params=params, timeout=TIMEOUT_SECS)
            # retry on rate-limit or server errors
            if r.status_code == 429 or 500 <= r.status_code < 600:
                retry_after = r.headers.get("Retry-After")
                sleep_for = float(retry_after) if (retry_after and retry_after.isdigit()) else backoff
                time.sleep(sleep_for)
                backoff *= 2
                continue
            return r
        except requests.RequestException as e:
            last_exc = e
            time.sleep(backoff)
            backoff *= 2

    if last_exc:
        raise last_exc
    raise requests.HTTPError("GET failed after retries")


def _cmc_btc_price(currency: str) -> BTCResult:
    """Fetch BTC price from CoinMarketCap using the Pro API."""
    if not CMC_KEY:
        raise RuntimeError("Missing COINMARKETCAP_API_KEY")

    url = "https://pro-api.coinmarketcap.com/v2/cryptocurrency/quotes/latest"
    headers = {
        "X-CMC_PRO_API_KEY": CMC_KEY,
        "User-Agent": USER_AGENT,
    }
    params = {"symbol": "BTC", "convert": currency.upper()}

    resp = _http_get(url, headers=headers, params=params)
    resp.raise_for_status()
    payload = resp.json()

    try:
        d = payload["data"]["BTC"][0]
        q = d["quote"][currency.upper()]

        return BTCResult(
            symbol="BTC",
            currency=currency.upper(),
            price=float(q["price"]),
            change_24h=float(q.get("percent_change_24h", 0.0)),
            volume=float(q.get("volume_24h", 0.0)),
            as_of=d.get("last_updated") or q.get("last_updated") or "",
            source="coinmarketcap",
        )
    except Exception as e:
        # Explicit error if schema doesn't match
        raise ValueError(f"Unexpected CoinMarketCap response shape: {e}")


# =========================
# Public MCP tool
# =========================
@mcp.tool
def get_btc_price(currency: str = "USD") -> Dict[str, Any]:
    """
    Get the latest BTC price in the given currency.

    Args:
      currency: e.g., "USD", "EUR", "JPY"

    Returns:
      {symbol, currency, price, change_24h, volume, as_of, source}

    Raises:
      RuntimeError if the API key is missing or the request fails.
    """
    result = _cmc_btc_price(currency)
    return asdict(result)


# =========================
# Entrypoint (stdio transport)
# =========================
if __name__ == "__main__":
    mcp.run()
