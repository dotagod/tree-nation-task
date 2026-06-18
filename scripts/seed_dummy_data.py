#!/usr/bin/env python3
"""Seed the running service with dummy visit data via the API."""

from __future__ import annotations

import argparse
import random
import sys
from datetime import datetime, timedelta, timezone

import httpx


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fill the in-memory store with dummy visit events (server must be running)."
    )
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="Base URL of the running service (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--customers",
        type=int,
        default=12,
        help="Number of distinct customers to create (default: 12)",
    )
    parser.add_argument(
        "--hours",
        type=int,
        default=24,
        help="Spread visits across this many past hours (default: 24, matches dashboard window)",
    )
    parser.add_argument(
        "--min-visits-per-hour",
        type=int,
        default=0,
        help="Minimum visits per hour bucket (default: 0)",
    )
    parser.add_argument(
        "--max-visits-per-hour",
        type=int,
        default=8,
        help="Maximum visits per hour bucket (default: 8)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducible data (default: 42)",
    )
    return parser.parse_args()


def random_timestamp_in_hour(
    hour_start: datetime, now: datetime, rng: random.Random
) -> datetime:
    hour_end = hour_start + timedelta(hours=1)
    latest = min(hour_end, now)
    if latest <= hour_start:
        return hour_start
    max_offset = int((latest - hour_start).total_seconds()) - 1
    max_offset = max(max_offset, 0)
    return hour_start + timedelta(seconds=rng.randint(0, max_offset))


def build_visits(
    *,
    customers: int,
    hours: int,
    min_visits_per_hour: int,
    max_visits_per_hour: int,
    rng: random.Random,
) -> list[tuple[str, datetime]]:
    now = datetime.now(timezone.utc)
    current_hour = now.replace(minute=0, second=0, microsecond=0)
    customer_ids = [f"cust-{i:03d}" for i in range(1, customers + 1)]
    visits: list[tuple[str, datetime]] = []

    for hour_offset in range(hours - 1, -1, -1):
        hour_start = current_hour - timedelta(hours=hour_offset)
        count = rng.randint(min_visits_per_hour, max_visits_per_hour)
        for _ in range(count):
            customer_id = rng.choice(customer_ids)
            timestamp = random_timestamp_in_hour(hour_start, now, rng)
            visits.append((customer_id, timestamp))

    visits.sort(key=lambda item: item[1])
    return visits


def configure_customer_thresholds(
    client: httpx.Client,
    base_url: str,
    customer_ids: list[str],
    rng: random.Random,
) -> None:
    base = base_url.rstrip("/")
    for customer_id in customer_ids:
        visits_per_tree = rng.randint(3, 10)
        response = client.put(
            f"{base}/api/customers/{customer_id}/config",
            json={"visits_per_tree": visits_per_tree},
        )
        response.raise_for_status()


def seed(
    base_url: str,
    visits: list[tuple[str, datetime]],
    rng: random.Random,
) -> None:
    url = f"{base_url.rstrip('/')}/api/visits"
    trees_planted = 0

    with httpx.Client(timeout=30.0) as client:
        try:
            client.get(f"{base_url.rstrip('/')}/api/config").raise_for_status()
        except httpx.HTTPError as exc:
            print(f"Cannot reach service at {base_url}: {exc}", file=sys.stderr)
            print("Start the server first: uvicorn app.main:app --reload", file=sys.stderr)
            sys.exit(1)

        customer_ids = sorted({customer_id for customer_id, _ in visits})
        configure_customer_thresholds(client, base_url, customer_ids, rng)
        print(f"Configured {len(customer_ids)} customers with visits-per-tree between 3 and 10.")

        for index, (customer_id, timestamp) in enumerate(visits, start=1):
            payload = {
                "customer_id": customer_id,
                "timestamp": timestamp.isoformat().replace("+00:00", "Z"),
            }
            response = client.post(url, json=payload)
            response.raise_for_status()
            body = response.json()
            if body.get("tree_just_planted"):
                trees_planted += 1

            if index % 50 == 0 or index == len(visits):
                print(f"Posted {index}/{len(visits)} visits...")

    unique_customers = len({customer_id for customer_id, _ in visits})
    print(
        f"Done. Posted {len(visits)} visits for {unique_customers} customers "
        f"({trees_planted} trees planted)."
    )
    print(f"Dashboard: {base_url.rstrip('/')}/")


def main() -> None:
    args = parse_args()
    if args.customers < 1:
        print("--customers must be at least 1", file=sys.stderr)
        sys.exit(1)
    if args.hours < 1:
        print("--hours must be at least 1", file=sys.stderr)
        sys.exit(1)
    if args.min_visits_per_hour < 0 or args.max_visits_per_hour < args.min_visits_per_hour:
        print("Invalid visit range per hour", file=sys.stderr)
        sys.exit(1)

    rng = random.Random(args.seed)
    visits = build_visits(
        customers=args.customers,
        hours=args.hours,
        min_visits_per_hour=args.min_visits_per_hour,
        max_visits_per_hour=args.max_visits_per_hour,
        rng=rng,
    )
    seed(args.base_url, visits, rng)


if __name__ == "__main__":
    main()
