from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class VisitRequest(BaseModel):
    customer_id: str = Field(..., min_length=1)
    timestamp: Optional[datetime] = None


class VisitResponse(BaseModel):
    customer_id: str
    total_visits: int
    trees_planted: int
    visits_toward_next_tree: int
    last_connection_at: datetime
    tree_just_planted: bool


class CustomerResponse(BaseModel):
    customer_id: str
    total_visits: int
    trees_planted: int
    visits_toward_next_tree: int
    last_connection_at: Optional[datetime]
    visits_per_tree: int


class CustomerListResponse(BaseModel):
    customers: list[CustomerResponse]


class CustomerConfigRequest(BaseModel):
    visits_per_tree: int = Field(..., ge=1)


class HourlyCustomerBucket(BaseModel):
    customer_id: str
    visits: int


class HourlyBucket(BaseModel):
    hour: datetime
    visits: int
    customers: list[HourlyCustomerBucket] = Field(default_factory=list)


class HourlyStatsResponse(BaseModel):
    buckets: list[HourlyBucket]


class TreePlantedEventResponse(BaseModel):
    customer_id: str
    planted_at: datetime
    visits_per_tree: int


class TreeEventsResponse(BaseModel):
    events: list[TreePlantedEventResponse]


class ConfigResponse(BaseModel):
    default_visits_per_tree: int
