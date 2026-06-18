from fastapi import APIRouter

from app.models import TreeEventsResponse
from app.services.visit_service import visit_service

router = APIRouter(prefix="/api/trees", tags=["trees"])


@router.get("/events", response_model=TreeEventsResponse)
def get_tree_events() -> TreeEventsResponse:
    return visit_service.get_tree_events()
