from fastapi import APIRouter

from app.models import CustomerConfigRequest, CustomerListResponse, CustomerResponse
from app.services.visit_service import visit_service

router = APIRouter(prefix="/api/customers", tags=["customers"])


@router.get("", response_model=CustomerListResponse)
def list_customers() -> CustomerListResponse:
    return visit_service.list_customers()


@router.get("/{customer_id}", response_model=CustomerResponse)
def get_customer(customer_id: str) -> CustomerResponse:
    return visit_service.get_customer(customer_id)


@router.put("/{customer_id}/config", response_model=CustomerResponse)
def set_customer_config(
    customer_id: str, payload: CustomerConfigRequest
) -> CustomerResponse:
    return visit_service.set_customer_config(customer_id, payload)
