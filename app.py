import json
import logging
import os
import threading
import time
import requests
import urllib.request
import urllib.error
from datetime import datetime, timezone
from flask import Flask, jsonify, render_template, request

BOM_API_URL = "https://api.weather.bom.gov.au/v1/locations/r1qcmpg/forecasts/daily"
FORECAST_FILE = os.path.join(os.path.dirname(__file__), "forecast.json")
REFRESH_INTERVAL_HOURS = 24
PORT = 5000

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)

# A simple in-memory cache for geocoding to avoid repeated lookups
GEOCODING_CACHE = {}


def fetch_forecast() -> bool:
    """Fetch forecast from BOM API and write to FORECAST_FILE. Returns True on success."""
    req = urllib.request.Request(
        BOM_API_URL,
        headers={"User-Agent": "Mozilla/5.0"}
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            raw = response.read()
        data = json.loads(raw)
        data["fetched_at"] = datetime.now(timezone.utc).isoformat()
        tmp_path = FORECAST_FILE + ".tmp"
        with open(tmp_path, "w") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp_path, FORECAST_FILE)
        logger.info("Forecast updated successfully.")
        return True
    except Exception as exc:
        logger.error("Failed to fetch forecast: %s", exc)
        return False


def is_cache_stale() -> bool:
    """Return True if forecast.json is missing or older than REFRESH_INTERVAL_HOURS."""
    if not os.path.exists(FORECAST_FILE):
        return True
    try:
        with open(FORECAST_FILE) as f:
            data = json.load(f)
        fetched_at = datetime.fromisoformat(data["fetched_at"])
        if fetched_at.tzinfo is None:
            fetched_at = fetched_at.replace(tzinfo=timezone.utc)
        age_hours = (datetime.now(timezone.utc) - fetched_at).total_seconds() / 3600
        return age_hours >= REFRESH_INTERVAL_HOURS
    except (KeyError, ValueError, OSError):
        return True


def start_background_refresh():
    """Daemon thread: fetch immediately if stale, then refresh every 24h."""
    def _loop():
        if is_cache_stale():
            logger.info("Cache stale or missing — fetching now.")
            fetch_forecast()
        while True:
            if not os.path.exists(FORECAST_FILE):
                sleep_secs = 300  # retry in 5 min if still no cache
            else:
                sleep_secs = REFRESH_INTERVAL_HOURS * 3600
            time.sleep(sleep_secs)
            logger.info("Refreshing forecast.")
            fetch_forecast()

    t = threading.Thread(target=_loop, daemon=True)
    t.start()
    logger.info("Background refresh thread started.")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/forecast", methods=["GET"])
def get_forecast():
    if not os.path.exists(FORECAST_FILE):
        return jsonify({"error": "No forecast data yet. Please wait a moment."}), 503
    try:
        with open(FORECAST_FILE) as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return jsonify({"error": "Forecast data is unavailable. Please try refreshing."}), 503
    return jsonify(data)


@app.route('/api/met-weather')
def get_met_weather():
    city = request.args.get('city')
    if not city:
        return jsonify({"message": "City parameter is required."}), 400

    # 1. Geocode city name to lat/lon
    try:
        city_key = city.lower()
        if city_key in GEOCODING_CACHE:
            lat, lon, name = GEOCODING_CACHE[city_key]
            logger.info(f"Geocoding cache hit for '{city}'.")
        else:
            logger.info(f"Geocoding cache miss for '{city}'. Querying API.")
            # Using Open-Meteo's free geocoding API
            geo_res = requests.get(
                "https://geocoding-api.open-meteo.com/v1/search",
                params={"name": city, "count": 1, "language": "en", "format": "json"},
                timeout=10
            )
            geo_res.raise_for_status()
            geo_data = geo_res.json()
            if not geo_data.get('results'):
                logger.warning(f"Geocoding for '{city}' returned no results.")
                return jsonify({"message": f"Could not find location for '{city}'."}), 404

            location = geo_data['results'][0]
            lat, lon, name = location['latitude'], location['longitude'], location['name']
            GEOCODING_CACHE[city_key] = (lat, lon, name)

    except requests.RequestException as e:
        logger.error(f"Failed to geocode city '{city}': {e}")
        return jsonify({"message": "Service for finding locations is currently unavailable."}), 503

    # 2. Fetch weather from MET Norway
    try:
        headers = {
            # MET.no requires a descriptive User-Agent.
            'User-Agent': 'WeatherApp/1.0 (https://your-github.com/your-repo)'
        }
        weather_res = requests.get(
            f"https://api.met.no/weatherapi/locationforecast/2.0/compact?lat={lat:.4f}&lon={lon:.4f}",
            headers=headers,
            timeout=10
        )
        weather_res.raise_for_status()
        weather_data = weather_res.json()

        # 3. Process data and return a simplified response for the frontend
        current_timeseries = weather_data['properties']['timeseries'][0]
        summary = current_timeseries['data']['next_1_hours']['summary']
        details = current_timeseries['data']['instant']['details']

        icon_symbol = summary['symbol_code']
        icon_descriptor = icon_symbol.split('_')[0]

        response_data = {
            "name": name,
            "temperature": details['air_temperature'],
            "summary": icon_symbol.replace("_", " ").title(),
            "icon_descriptor": icon_descriptor
        }
        return jsonify(response_data)

    except (requests.RequestException, KeyError, IndexError) as e:
        logger.error(f"Failed to get or parse MET weather for '{name}': {e}")
        return jsonify({"message": "The weather service is currently unavailable or returned invalid data."}), 503


@app.route("/api/refresh", methods=["POST"])
def refresh_forecast():
    success = fetch_forecast()
    if not os.path.exists(FORECAST_FILE):
        return jsonify({"error": "Fetch failed and no cached data available."}), 503
    try:
        with open(FORECAST_FILE) as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return jsonify({"error": "Forecast data is unavailable. Please try refreshing."}), 503
    if not success:
        data["refresh_failed"] = True
    return jsonify(data)


if __name__ == "__main__":
    start_background_refresh()
    app.run(host="0.0.0.0", port=PORT, debug=False)
