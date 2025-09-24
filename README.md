# FastMCP Course – Sample MCP Servers and Client

This repo contains several small, focused Model Context Protocol (MCP) servers built with FastMCP, plus a tiny async client. They demonstrate tools, resources, structured outputs, env loading, and both stdio and HTTP transports.

Included servers and client:
- `hello.py` – minimal HTTP MCP with a `say_hello` tool and a demo client in `client.py`.
- `btc_price_server.py` – fetches live BTC price from CoinMarketCap, with caching and .env support.
- `btc_trend_server.py` – computes a BTC SMA-based trend signal by chaining live price + moving-average analysis.
- `weather_server.py` – deterministic, stubbed weather/forecast service returning typed dataclasses.
- `mcp_docs_server.py` – in-memory knowledge base with resources and upsert tools.
- `password_server.py` – strong password generator with entropy metadata.
- `client.py` – example of calling a tool on an HTTP MCP server.


## Prerequisites

- Python 3.10+ (tested with 3.12)
- macOS terminal uses zsh by default (commands below assume zsh)


## Install dependencies

```
pip install -r requirements.txt
```


## Environment variables (.env)

BTC price and trend servers need a secret:

- `COINMARKETCAP_API_KEY` – get a free API key at https://coinmarketcap.com/api/

Create a file named `.env` at the repo root and add:

```
COINMARKETCAP_API_KEY=your_key_here
```

Notes
- `btc_price_server.py` and `btc_trend_server.py` auto-load `.env` from the current working directory or a `.env` next to each script.
- You can also export in your shell for one session:
  - zsh: `export COINMARKETCAP_API_KEY=your_key_here`


## How to run each server

All servers can be started directly. For stdio use in Copilot MCP Developer Mode, prefer `transport="stdio"`. Where HTTP is shown, you can exercise them with the included `client.py` or your own HTTP MCP client.

### 1) Hello World server (HTTP)

Starts an HTTP MCP server on port 8000 and exposes a `say_hello(name)` tool.

Run:

```
python3 hello.py
```

Try the client (calls `say_hello`):

```
python3 client.py
```

Expected output:
```
Hello, World!
```

### 2) Bitcoin Price server (stdio)

Provides tool `get_btc_price(vs_currency)` and resource `price://btc/{vs_currency}`. Caches responses for ~10s.

Run:

```
python3 btc_price_server.py
```

Tool contract
- Input: `vs_currency` one of USD, EUR, GBP, CAD, AUD, CHF, JPY, INR (default USD)
- Output JSON: `{ symbol, vs_currency, price, percent_change_24h, last_updated, source, ... }` or `{ error, ... }`

Common errors
- `missing_api_key` – set `COINMARKETCAP_API_KEY` in your environment.
- `http_401/403/429` – auth/rate-limits; check key/plan.

### 2b) BTC Trend server (stdio)

Combines live BTC price (CoinMarketCap) with a short in-memory price history to compute short/long simple moving averages and emit a quick trend signal.

Run:

```
python3 btc_trend_server.py
```

Tool
- `get_btc_trend_signal(vs_currency="USD", lookback_minutes=60, short_window=5, long_window=20, neutral_threshold_bps=25.0, simulate_if_needed=True)`

Returns JSON like:
`{ symbol, vs_currency, price, last_updated, sma_short, sma_long, signal, ratio_bps, threshold_bps, points_used, source, attribution, endpoint, note }`

Notes
- Requires `COINMARKETCAP_API_KEY` (same as the price server).
- Keeps a small in-memory history per currency; if history is short and `simulate_if_needed=true`, the server backfills a small synthetic price series to enable SMA calculation.
 - Spot price fetches are cached for ~10 seconds to avoid hammering the API.
 - History uses ~1-minute granularity and is capped to a rolling buffer.

Resource
- `trend://btc/{vs_currency}` – resource wrapper that returns the same payload as the tool with defaults.

Example output

```
{
  "symbol": "BTC",
  "vs_currency": "USD",
  "price": 113731.52,
  "last_updated": "2025-09-24T17:02:00.000Z",
  "sma_short": 113810.12,
  "sma_long": 113914.25,
  "signal": "neutral",
  "ratio_bps": -9.14,
  "threshold_bps": 25.0,
  "points_used": 60,
  "source": "coinmarketcap",
  "attribution": "Data from CoinMarketCap",
  "endpoint": "quotes/latest",
  "note": "simulated 59 synthetic points to fill history"
}
```

### 3) Weather server (stdio, stubbed)

Deterministic weather for demo purposes. Returns typed dataclasses serialized by FastMCP.

Run:

```
python3 weather_server.py
```

Tools
- `get_weather(city, units="imperial"|"metric") -> WeatherNow`
- `get_forecast(city, days=5, units) -> WeatherForecast` (days 1..7)

### 4) Docs & KB server (stdio)

Exposes resource URIs and upsert tools for a simple in-memory knowledge base.

Run:

```
python3 mcp_docs_server.py
```

Resources
- `doc://project/{slug}` – fetch a project doc
- `help://article/{aid}` – fetch a help article

Tools
- `list_resources(kind="all"|"project"|"helpdesk")`
- `upsert_project_doc(slug, title, body, tags=[])`
- `upsert_help_article(aid, title, body, tags=[])`

### 5) Password generator (stdio)

Run:

```
python3 password_server.py
```

Tool
- `generate_password(length=16, include_upper=True, include_lower=True, include_digits=True, include_symbols=True, exclude_ambiguous=True, require_each_class=True) -> PasswordResult`

Output includes the generated password, length, pool size, and estimated entropy (bits).


## Using with GitHub Copilot MCP (Developer Mode)

You can register these servers in your MCP config to call their tools/resources from Copilot. For stdio servers, start them via your MCP configuration, or run them manually and use stdio transport from Copilot. For the HTTP hello server, point clients to `http://localhost:8000/mcp`.

There is also a `time-mcp.py` JSON snippet demonstrating how to register the community `mcp-server-time` via `uvx`.


## Project structure

- `hello.py` – HTTP server with `say_hello`
- `client.py` – async example client that calls `say_hello`
- `btc_price_server.py` – CoinMarketCap BTC price server (requires API key)
- `weather_server.py` – stubbed weather server
- `mcp_docs_server.py` – docs/helpdesk resources + tools
- `password_server.py` – password generator
- `time-mcp.py` – example MCP config snippet for a time server (JSON content)
- `requirements.txt` – Python deps
- `.env` – optional env file for secrets like API keys


## Troubleshooting

- ImportError fastmcp: Ensure `pip install -r requirements.txt` ran successfully and you’re using the right Python.
- Cannot connect to HTTP server: Verify it’s running and listening on `http://localhost:8000/mcp`.
- CoinMarketCap errors: Confirm API key, plan, and that your `vs_currency` is one of the allowed values.


## License

For educational use as part of the FastMCP course. Adapt as needed for your own experiments.
