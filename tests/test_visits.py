from datetime import datetime, timezone

import pytest

from app.config import settings
from app.models import CustomerConfigRequest
from app.services.visit_service import VisitService
from app.store import store


@pytest.fixture(autouse=True)
def clear_store():
    store.clear()
    yield
    store.clear()


@pytest.fixture
def service():
    return VisitService()


def test_record_visit_increments_count(service):
    ts = datetime.now(timezone.utc)
    result = service.record_visit("cust-a", ts)

    assert result.total_visits == 1
    assert result.trees_planted == 0
    assert result.last_connection_at == ts


def test_trees_planted_at_interval(service, monkeypatch):
    monkeypatch.setattr(settings, "visits_per_tree", 3)

    base = datetime.now(timezone.utc)
    for i in range(3):
        result = service.record_visit("cust-a", base.replace(second=i))

    assert result.total_visits == 3
    assert result.visits_toward_next_tree == 0
    assert result.trees_planted == 1
    assert result.tree_just_planted is True


def test_progress_carries_over_when_threshold_increases(service, monkeypatch):
    monkeypatch.setattr(settings, "visits_per_tree", 3)

    base = datetime.now(timezone.utc)
    for i in range(2):
        service.record_visit("cust-a", base.replace(second=i))

    service.set_customer_config("cust-a", CustomerConfigRequest(visits_per_tree=10))
    customer = service.get_customer("cust-a")

    assert customer.total_visits == 2
    assert customer.visits_toward_next_tree == 2
    assert customer.trees_planted == 0


def test_per_customer_visits_per_tree(service, monkeypatch):
    monkeypatch.setattr(settings, "visits_per_tree", 5)

    service.set_customer_config("cust-a", CustomerConfigRequest(visits_per_tree=3))

    base = datetime.now(timezone.utc)
    for i in range(3):
        result = service.record_visit("cust-a", base.replace(second=i))

    assert result.trees_planted == 1
    assert result.tree_just_planted is True


def test_hourly_stats_fill_empty_buckets(service):
    ts = datetime.now(timezone.utc)
    service.record_visit("cust-a", ts)

    stats = service.get_hourly_stats(hours=3)
    assert len(stats.buckets) == 3
    assert sum(bucket.visits for bucket in stats.buckets) == 1
    assert sum(len(bucket.customers) for bucket in stats.buckets) == 1
