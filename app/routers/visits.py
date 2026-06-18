from fastapi import APIRouter, status

from app.models import VisitRequest, VisitResponse
from app.services.visit_service import visit_service

router = APIRouter(prefix="/api/visits", tags=["visits"])


@router.post("", response_model=VisitResponse, status_code=status.HTTP_201_CREATED)
def create_visit(payload: VisitRequest) -> VisitResponse:
    return visit_service.record_visit(payload.customer_id, payload.timestamp)
