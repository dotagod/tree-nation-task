from fastapi import APIRouter, Query

from app.models import ConfigResponse, HourlyStatsResponse
from app.services.visit_service import visit_service

router = APIRouter(prefix="/api", tags=["stats"])


@router.get("/stats/hourly", response_model=HourlyStatsResponse)
def get_hourly_stats(hours: int = Query(default=24, ge=1, le=168)) -> HourlyStatsResponse:
    return visit_service.get_hourly_stats(hours)


@router.get("/config", response_model=ConfigResponse)
def get_config() -> ConfigResponse:
    return visit_service.get_config()
