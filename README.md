# Bitcoin Price MCP (CoinMarketCap)

This MCP fetches the current BTC spot price from CoinMarketCap.

## Setup

- Create a free API key: https://coinmarketcap.com/api/
- Install dependencies (once):
  pip install -r requirements.txt
- Add the key to your environment via either method:

1) Using a .env file (recommended for local dev)
   - Copy `.env.example` to `.env`
   - Edit `.env` and set `COINMARKETCAP_API_KEY=your_key_here`
   - The server loads `.env` from your current working directory or next to `btc_price_server.py`.

2) Export in your shell (temporary for this session)
   - macOS zsh example:
     export COINMARKETCAP_API_KEY=your_key_here

## Run

- From VS Code Copilot MCP (stdio): the project includes `.vscode/mcp.json` with a server named "Bitcoin MCP".
- Or run directly:
  python3 btc_price_server.py

Then call the tool `get_btc_price` with an optional `vs_currency` (USD, EUR, GBP, CAD, AUD, CHF, JPY, INR).
