# weather_server.py
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import List, Literal, Dict

import requests
from fastmcp import FastMCP

# -----------------------------------------------------------------------------
# Types & Data Models
# -----------------------------------------------------------------------------

Units = Literal["imperial", "metric"]

@dataclass
class Location:
    city: str
    country: str

@dataclass
class WeatherNow:
    location: Location
    temperature: float
    humidity: int
    condition: str
    observed_at: str
    units: Units

@dataclass
class ForecastDay:
    date: str
    high: float
    low: float
    condition: str  # simple daily condition (optional aggregation)

@dataclass
class WeatherForecast:
    location: Location
    days: List[ForecastDay]
    units: Units


# -----------------------------------------------------------------------------
# Server Initialization
# -----------------------------------------------------------------------------

mcp = FastMCP("Weather MCP (OpenWeather)")


# -----------------------------------------------------------------------------
# OpenWeather Helpers
# -----------------------------------------------------------------------------

OW_BASE = "https://api.openweathermap.org/data/2.5"
OW_TIMEOUT = 12  # seconds

def get_api_key() -> str:
    key = os.environ.get("OPENWEATHER_API_KEY")
    if not key:
        raise RuntimeError("OPENWEATHER_API_KEY not set")
    return key

def ow_units(units: Units) -> str:
    # Maps our "imperial|metric" to OpenWeather's units parameter
    return "imperial" if units == "imperial" else "metric"

def fetch_current_from_ow(city: str, units: Units) -> dict:
    params = {
        "q": city,
        "appid": get_api_key(),
        "units": ow_units(units),
    }
    try:
        r = requests.get(f"{OW_BASE}/weather", params=params, timeout=OW_TIMEOUT)
        r.raise_for_status()
        return r.json()
    except requests.HTTPError as e:
        msg = _safe_error_message(e)
        raise ValueError(f"OpenWeather error (current): {msg}")
    except requests.RequestException as e:
        raise RuntimeError(f"Network error (current): {e}")

def fetch_forecast_from_ow(city: str, units: Units) -> dict:
    params = {
        "q": city,
        "appid": get_api_key(),
        "units": ow_units(units),
    }
    try:
        r = requests.get(f"{OW_BASE}/forecast", params=params, timeout=OW_TIMEOUT)
        r.raise_for_status()
        return r.json()
    except requests.HTTPError as e:
        msg = _safe_error_message(e)
        raise ValueError(f"OpenWeather error (forecast): {msg}")
    except requests.RequestException as e:
        raise RuntimeError(f"Network error (forecast): {e}")

def _safe_error_message(e: requests.HTTPError) -> str:
    try:
        if e.response is not None and e.response.headers.get("Content-Type", "").startswith("application/json"):
            return e.response.json().get("message", str(e))
    except Exception:
        pass
    return str(e)

def iso_from_unix(ts: int | None) -> str:
    if not ts:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    return datetime.fromtimestamp(ts, tz=timezone.utc).replace(microsecond=0).isoformat()


# -----------------------------------------------------------------------------
# Mapping Functions
# -----------------------------------------------------------------------------

def map_current_to_dataclass(payload: dict, units: Units) -> WeatherNow:
    city_name = payload.get("name") or "Unknown"
    sys = payload.get("sys", {}) or {}
    country = sys.get("country", "US")

    main = payload.get("main", {}) or {}
    temp = float(main.get("temp"))
    humidity = int(main.get("humidity", 0))

    wx_arr = payload.get("weather") or []
    condition = (wx_arr[0].get("description") if wx_arr else "Unknown").title()

    observed_iso = iso_from_unix(payload.get("dt"))

    return WeatherNow(
        location=Location(city=city_name, country=country),
        temperature=round(temp, 1),
        humidity=humidity,
        condition=condition,
        observed_at=observed_iso,
        units=units,
    )

def aggregate_to_daily_high_lows(forecast_payload: dict, units: Units, days: int) -> List[ForecastDay]:
    """
    OpenWeather 'forecast' returns 3-hourly entries (~40 blocks over ~5 days).
    Aggregate into daily highs/lows by UTC date. For 'condition', we pick the
    most frequent main descriptor of the day (simple mode).
    """
    from collections import defaultdict, Counter

    list_blocks = forecast_payload.get("list") or []

    buckets: Dict[str, Dict[str, float]] = defaultdict(lambda: {"high": float("-inf"), "low": float("inf")})
    conditions_per_day: Dict[str, Counter] = defaultdict(Counter)

    for block in list_blocks:
        main = block.get("main", {}) or {}
        temp = float(main.get("temp"))

        dt_unix = block.get("dt")
        date_iso = datetime.fromtimestamp(dt_unix, tz=timezone.utc).date().isoformat() if dt_unix else datetime.now(timezone.utc).date().isoformat()

        buckets[date_iso]["high"] = max(buckets[date_iso]["high"], temp)
        buckets[date_iso]["low"] = min(buckets[date_iso]["low"], temp)

        wx_arr = block.get("weather") or []
        cond = (wx_arr[0].get("description") if wx_arr else "—").title()
        conditions_per_day[date_iso][cond] += 1

    sorted_dates = sorted(buckets.keys())[:days]

    result: List[ForecastDay] = []
    for d in sorted_dates:
        high = buckets[d]["high"]
        low = buckets[d]["low"]
        if high == float("-inf") or low == float("inf"):
            continue
        # Pick the daily "mode" condition
        cond = "—"
        if conditions_per_day[d]:
            cond = conditions_per_day[d].most_common(1)[0][0]
        result.append(ForecastDay(
            date=d,
            high=round(high, 1),
            low=round(low, 1),
            condition=cond,
        ))
    return result

def map_forecast_to_dataclass(payload: dict, units: Units, requested_days: int, fallback_city: str) -> WeatherForecast:
    city_blob = payload.get("city", {}) or {}
    city_name = city_blob.get("name") or fallback_city.title()
    country = city_blob.get("country", "US")

    days = aggregate_to_daily_high_lows(payload, units, requested_days)
    return WeatherForecast(
        location=Location(city=city_name, country=country),
        days=days,
        units=units,
    )


# -----------------------------------------------------------------------------
# Tools
# -----------------------------------------------------------------------------

@mcp.tool()
def get_weather(
    city: str,
    units: Units = "imperial",
) -> WeatherNow:
    """
    Return live current weather for a city via OpenWeather API.
    Args:
      city: City name (e.g., "San Diego")
      units: "imperial" or "metric"
    """
    if units not in ("imperial", "metric"):
        raise ValueError("units must be 'imperial' or 'metric'")

    payload = fetch_current_from_ow(city, units)
    return map_current_to_dataclass(payload, units)

@mcp.tool()
def get_forecast(
    city: str,
    days: int = 5,
    units: Units = "imperial",
) -> WeatherForecast:
    """
    Return a live multi-day forecast (aggregated daily highs/lows) via OpenWeather.
    Args:
      city: City name (e.g., "Austin")
      days: Number of days (1..7)
      units: "imperial" or "metric"
    """
    if not (1 <= days <= 7):
        raise ValueError("days must be between 1 and 7")
    if units not in ("imperial", "metric"):
        raise ValueError("units must be 'imperial' or 'metric'")

    payload = fetch_forecast_from_ow(city, units)
    mapped = map_forecast_to_dataclass(payload, units, days, fallback_city=city)
    if len(mapped.days) > days:
        mapped.days = mapped.days[:days]
    return mapped


# -----------------------------------------------------------------------------
# Entrypoint
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    # Start the MCP server (stdio transport by default)
    mcp.run()
