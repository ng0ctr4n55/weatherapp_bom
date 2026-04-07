"""MCP server exposing the BOM weather forecast to Claude Desktop.

Reuses fetch/cache helpers from app.py so the Flask app and MCP server
share the same forecast.json cache file.

Run directly:
    python mcp_server.py

Claude Desktop config (claude_desktop_config.json):
    {
      "mcpServers": {
        "bom-weather": {
          "command": "python",
          "args": ["C:/Users/ltra0018/Documents/weatherapp_bom/mcp_server.py"]
        }
      }
    }
"""
import json
import os
from typing import Any

from mcp.server.fastmcp import FastMCP

from app import FORECAST_FILE, fetch_forecast, is_cache_stale

mcp = FastMCP("bom-weather")


def _load_cached_forecast() -> dict[str, Any]:
    """Read forecast.json, fetching first if the cache is stale or missing."""
    if is_cache_stale():
        fetch_forecast()
    if not os.path.exists(FORECAST_FILE):
        raise RuntimeError("No forecast data available and fetch failed.")
    with open(FORECAST_FILE) as f:
        return json.load(f)


@mcp.tool()
def get_forecast() -> dict[str, Any]:
    """Return the full 7-day BOM forecast for Fraser Rise, VIC.

    Auto-refreshes from the BOM API if the local cache is older than 24 hours.
    """
    return _load_cached_forecast()


@mcp.tool()
def refresh_forecast() -> dict[str, Any]:
    """Force an immediate refresh from the BOM API, bypassing the cache.

    Returns the freshly fetched forecast, or the stale cache with a
    'refresh_failed' flag if the upstream call fails.
    """
    success = fetch_forecast()
    with open(FORECAST_FILE) as f:
        data = json.load(f)
    if not success:
        data["refresh_failed"] = True
    return data


@mcp.tool()
def get_today() -> dict[str, Any]:
    """Return a concise summary of today's weather for Fraser Rise, VIC.

    TODO: implement this — see the conversation for the design discussion.
    """
    raise NotImplementedError("get_today() — implement me")


if __name__ == "__main__":
    mcp.run()
