

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import requests

app = FastAPI(
    title="GEO AI API",
    description="Location and environmental recommendations for outdoor activities",
    version="1.0.0"
)


class RecommendationRequest(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    activity: str = "outdoor walking"


@app.get("/")
def home():
    return {
        "project": "GEO AI",
        "status": "online",
        "message": "GEO AI API is running"
    }


@app.post("/recommend")
def recommend(request: RecommendationRequest):
    try:
        weather_url = "https://api.open-meteo.com/v1/forecast"
        weather_params = {
            "latitude": request.latitude,
            "longitude": request.longitude,
            "hourly": "temperature_2m,precipitation",
            "forecast_days": 2,
            "timezone": "auto"
        }

        weather_response = requests.get(
            weather_url, params=weather_params, timeout=20
        )
        weather_response.raise_for_status()
        weather = weather_response.json()

        air_url = "https://air-quality-api.open-meteo.com/v1/air-quality"
        air_params = {
            "latitude": request.latitude,
            "longitude": request.longitude,
            "hourly": "pm2_5,us_aqi",
            "forecast_days": 2,
            "timezone": "auto"
        }

        air_response = requests.get(
            air_url, params=air_params, timeout=20
        )
        air_response.raise_for_status()
        air = air_response.json()

        weather_hour = weather.get("hourly", {})
        air_hour = air.get("hourly", {})
        weather_times = weather_hour.get("time", [])
        air_times = air_hour.get("time", [])

        if not weather_times or not air_times:
            raise HTTPException(
                status_code=502,
                detail="Forecast data is unavailable"
            )

        required_weather = ("temperature_2m", "precipitation")
        required_air = ("pm2_5", "us_aqi")

        if any(not weather_hour.get(key) for key in required_weather):
            raise HTTPException(
                status_code=502,
                detail="Required weather forecast fields are missing"
            )

        if any(not air_hour.get(key) for key in required_air):
            raise HTTPException(
                status_code=502,
                detail="Required air-quality forecast fields are missing"
            )

        return {
            "activity": request.activity,
            "latitude": request.latitude,
            "longitude": request.longitude,
            "forecast_time": weather_times[0],
            "temperature_c": weather_hour["temperature_2m"][0],
            "precipitation_mm": weather_hour["precipitation"][0],
            "pm25": air_hour["pm2_5"][0],
            "us_aqi": air_hour["us_aqi"][0],
            "note": (
                "Environmental forecast data only. "
                "This endpoint does not yet apply the full GEO AI "
                "scoring engine or provide a medical safety guarantee."
            )
        }

    except HTTPException:
        raise

    except requests.RequestException as exc:
        print(f"Open-Meteo request error: {exc}", flush=True)
        raise HTTPException(
            status_code=502,
            detail=(
                f"Environmental data request failed: "
                f"{type(exc).__name__}: {exc}"
            )
        ) from exc

    except (KeyError, IndexError, TypeError) as exc:
        print(f"Forecast data processing error: {exc}", flush=True)
        raise HTTPException(
            status_code=502,
            detail=(
                f"Forecast data processing failed: "
                f"{type(exc).__name__}: {exc}"
            )
        ) from exc
