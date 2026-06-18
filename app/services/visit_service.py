from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException

from app.config import settings
from app.models import (
    ConfigResponse,
    CustomerConfigRequest,
    CustomerListResponse,
    CustomerResponse,
    HourlyBucket,
    HourlyCustomerBucket,
    HourlyStatsResponse,
    TreeEventsResponse,
    TreePlantedEventResponse,
    VisitResponse,
)
from app.store import CustomerRecord, store


class VisitService:
    def record_visit(self, customer_id: str, timestamp: Optional[datetime]) -> VisitResponse:
        ts = timestamp or datetime.now(timezone.utc)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        else:
            ts = ts.astimezone(timezone.utc)

        now = datetime.now(timezone.utc)
        if ts > now + timedelta(minutes=5):
            raise HTTPException(status_code=422, detail="Timestamp cannot be more than 5 minutes in the future")

        result = store.record_visit(customer_id, ts, settings.visits_per_tree)
        customer = result.customer

        return VisitResponse(
            customer_id=customer.customer_id,
            total_visits=customer.total_visits,
            trees_planted=customer.trees_planted,
            visits_toward_next_tree=customer.visits_toward_next_tree,
            last_connection_at=customer.last_connection_at,
            tree_just_planted=result.tree_just_planted,
        )

    def _customer_response(self, customer: CustomerRecord) -> CustomerResponse:
        return CustomerResponse(
            customer_id=customer.customer_id,
            total_visits=customer.total_visits,
            trees_planted=customer.trees_planted,
            visits_toward_next_tree=customer.visits_toward_next_tree,
            last_connection_at=customer.last_connection_at,
            visits_per_tree=customer.visits_per_tree,
        )

    def get_customer(self, customer_id: str) -> CustomerResponse:
        customer = store.get_customer(customer_id)
        if customer is None:
            raise HTTPException(status_code=404, detail="Customer not found")

        return self._customer_response(customer)

    def list_customers(self) -> CustomerListResponse:
        customers = [self._customer_response(customer) for customer in store.list_customers()]
        return CustomerListResponse(customers=customers)

    def set_customer_config(
        self, customer_id: str, payload: CustomerConfigRequest
    ) -> CustomerResponse:
        customer = store.set_visits_per_tree(
            customer_id,
            payload.visits_per_tree,
            settings.visits_per_tree,
        )
        return self._customer_response(customer)

    def get_hourly_stats(self, hours: int) -> HourlyStatsResponse:
        if hours < 1 or hours > 168:
            raise HTTPException(status_code=422, detail="hours must be between 1 and 168")

        buckets = [
            HourlyBucket(
                hour=hour,
                visits=count,
                customers=[
                    HourlyCustomerBucket(
                        customer_id=customer.customer_id,
                        visits=customer.visits,
                    )
                    for customer in customers
                ],
            )
            for hour, count, customers in store.get_hourly_customer_stats(hours)
        ]
        return HourlyStatsResponse(buckets=buckets)

    def get_tree_events(self) -> TreeEventsResponse:
        events = [
            TreePlantedEventResponse(
                customer_id=event.customer_id,
                planted_at=event.planted_at,
                visits_per_tree=event.visits_per_tree,
            )
            for event in store.get_tree_events()
        ]
        return TreeEventsResponse(events=events)

    def get_config(self) -> ConfigResponse:
        return ConfigResponse(default_visits_per_tree=settings.visits_per_tree)


visit_service = VisitService()
