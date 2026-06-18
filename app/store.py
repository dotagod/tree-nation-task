from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Dict, List, Optional, Tuple


@dataclass
class CustomerRecord:
    customer_id: str
    total_visits: int = 0
    visits_toward_next_tree: int = 0
    trees_planted: int = 0
    last_connection_at: Optional[datetime] = None
    visits_per_tree: int = 5


@dataclass
class TreePlantedEvent:
    customer_id: str
    planted_at: datetime
    visits_per_tree: int


@dataclass
class VisitRecordResult:
    customer: CustomerRecord
    tree_just_planted: bool


@dataclass
class HourlyCustomerStat:
    customer_id: str
    visits: int


@dataclass
class InMemoryStore:
    customers: Dict[str, CustomerRecord] = field(default_factory=dict)
    hourly_visits: Dict[str, int] = field(default_factory=dict)
    hourly_customer_visits: Dict[str, Dict[str, int]] = field(default_factory=dict)
    tree_events: List[TreePlantedEvent] = field(default_factory=list)
    _lock: Lock = field(default_factory=Lock)

    def _get_or_create_customer(
        self, customer_id: str, default_visits_per_tree: int
    ) -> CustomerRecord:
        if customer_id not in self.customers:
            self.customers[customer_id] = CustomerRecord(
                customer_id=customer_id,
                visits_per_tree=default_visits_per_tree,
            )
        return self.customers[customer_id]

    def _apply_tree_threshold(
        self, customer: CustomerRecord, timestamp: datetime
    ) -> bool:
        tree_just_planted = False
        while customer.visits_toward_next_tree >= customer.visits_per_tree:
            customer.trees_planted += 1
            customer.visits_toward_next_tree -= customer.visits_per_tree
            self.tree_events.append(
                TreePlantedEvent(
                    customer_id=customer.customer_id,
                    planted_at=timestamp,
                    visits_per_tree=customer.visits_per_tree,
                )
            )
            tree_just_planted = True
        return tree_just_planted

    def record_visit(
        self,
        customer_id: str,
        timestamp: datetime,
        default_visits_per_tree: int,
    ) -> VisitRecordResult:
        bucket_key = _hour_bucket_key(timestamp)
        with self._lock:
            customer = self._get_or_create_customer(customer_id, default_visits_per_tree)
            customer.total_visits += 1
            customer.last_connection_at = timestamp
            customer.visits_toward_next_tree += 1
            self.hourly_visits[bucket_key] = self.hourly_visits.get(bucket_key, 0) + 1
            hour_customers = self.hourly_customer_visits.setdefault(bucket_key, {})
            hour_customers[customer_id] = hour_customers.get(customer_id, 0) + 1

            tree_just_planted = self._apply_tree_threshold(customer, timestamp)
            return VisitRecordResult(customer=customer, tree_just_planted=tree_just_planted)

    def set_visits_per_tree(
        self,
        customer_id: str,
        visits_per_tree: int,
        default_visits_per_tree: int,
    ) -> CustomerRecord:
        with self._lock:
            customer = self._get_or_create_customer(customer_id, default_visits_per_tree)
            customer.visits_per_tree = visits_per_tree
            self._apply_tree_threshold(customer, datetime.now(timezone.utc))
            return customer

    def get_customer(self, customer_id: str) -> Optional[CustomerRecord]:
        with self._lock:
            return self.customers.get(customer_id)

    def list_customers(self) -> List[CustomerRecord]:
        with self._lock:
            return sorted(self.customers.values(), key=lambda customer: customer.customer_id)

    def get_tree_events(self) -> List[TreePlantedEvent]:
        with self._lock:
            return list(self.tree_events)

    def get_hourly_stats(
        self, hours: int, now: Optional[datetime] = None
    ) -> List[Tuple[datetime, int]]:
        reference = now or datetime.now(timezone.utc)
        if reference.tzinfo is None:
            reference = reference.replace(tzinfo=timezone.utc)

        start = reference.replace(minute=0, second=0, microsecond=0) - timedelta(hours=hours - 1)
        buckets: List[Tuple[datetime, int]] = []

        with self._lock:
            for i in range(hours):
                hour = start + timedelta(hours=i)
                key = _hour_bucket_key(hour)
                buckets.append((hour, self.hourly_visits.get(key, 0)))

        return buckets

    def get_hourly_customer_stats(
        self, hours: int, now: Optional[datetime] = None
    ) -> List[Tuple[datetime, int, List[HourlyCustomerStat]]]:
        reference = now or datetime.now(timezone.utc)
        if reference.tzinfo is None:
            reference = reference.replace(tzinfo=timezone.utc)

        start = reference.replace(minute=0, second=0, microsecond=0) - timedelta(hours=hours - 1)
        buckets: List[Tuple[datetime, int, List[HourlyCustomerStat]]] = []

        with self._lock:
            for i in range(hours):
                hour = start + timedelta(hours=i)
                key = _hour_bucket_key(hour)
                total_visits = self.hourly_visits.get(key, 0)
                customer_counts = self.hourly_customer_visits.get(key, {})
                customers = [
                    HourlyCustomerStat(
                        customer_id=customer_id,
                        visits=visit_count,
                    )
                    for customer_id, visit_count in sorted(customer_counts.items())
                ]
                buckets.append((hour, total_visits, customers))

        return buckets

    def clear(self) -> None:
        with self._lock:
            self.customers.clear()
            self.hourly_visits.clear()
            self.hourly_customer_visits.clear()
            self.tree_events.clear()


def _hour_bucket_key(timestamp: datetime) -> str:
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    else:
        timestamp = timestamp.astimezone(timezone.utc)
    return timestamp.strftime("%Y-%m-%dT%H")


store = InMemoryStore()
