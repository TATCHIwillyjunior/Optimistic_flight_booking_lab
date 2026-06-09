import asyncio

import httpx
import pytest

from app.main import app


@pytest.fixture
async def client() -> httpx.AsyncClient:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


async def reset(client: httpx.AsyncClient, scenario: str = "last-seat") -> None:
    response = await client.post("/admin/reset", json={"scenario": scenario})
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_flight_resource_exposes_state(client: httpx.AsyncClient) -> None:
    await reset(client, "last-seat")

    response = await client.get("/flights/AF123")

    assert response.status_code == 200
    data = response.json()
    assert data["remaining_seats"] == 1
    assert data["version"] == 0
    assert data["bookings_count"] == 0


@pytest.mark.asyncio
async def test_booking_advances_flight_state(client: httpx.AsyncClient) -> None:
    await reset(client, "last-seat")

    response = await client.post(
        "/flights/AF123/book",
        json={"passenger_name": "alice", "expected_version": 0},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["flight_version"] == 1
    assert data["remaining_seats"] == 0

    flight_response = await client.get("/flights/AF123")
    flight = flight_response.json()
    assert flight["version"] == 1
    assert flight["bookings_count"] == 1


@pytest.mark.asyncio
async def test_second_write_from_same_observation_is_conflict(client: httpx.AsyncClient) -> None:
    await reset(client, "last-seat")

    alice = await client.post(
        "/flights/AF123/book",
        json={"passenger_name": "alice", "expected_version": 0},
    )
    bob = await client.post(
        "/flights/AF123/book",
        json={"passenger_name": "bob", "expected_version": 0},
    )

    assert alice.status_code == 201
    assert bob.status_code == 409
    assert bob.json()["detail"]["error"] == "VERSION_CONFLICT"

    flight = (await client.get("/flights/AF123")).json()
    assert flight["bookings_count"] == 1


@pytest.mark.asyncio
async def test_parallel_writes_from_same_observation_preserve_capacity(client: httpx.AsyncClient) -> None:
    await reset(client, "last-seat")
    initial = (await client.get("/flights/AF123")).json()
    expected_version = initial["version"]

    alice, bob = await asyncio.gather(
        client.post(
            "/flights/AF123/book",
            json={"passenger_name": "alice", "expected_version": expected_version},
        ),
        client.post(
            "/flights/AF123/book",
            json={"passenger_name": "bob", "expected_version": expected_version},
        ),
    )

    statuses = [alice.status_code, bob.status_code]
    assert statuses.count(201) == 1
    assert statuses.count(409) == 1

    flight = (await client.get("/flights/AF123")).json()
    assert flight["remaining_seats"] == 0
    assert flight["bookings_count"] == 1
    assert flight["version"] == 1


@pytest.mark.asyncio
async def test_booking_request_must_include_observed_state(client: httpx.AsyncClient) -> None:
    await reset(client, "last-seat")

    response = await client.post(
        "/flights/AF123/book",
        json={"passenger_name": "alice"},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_two_seat_flight_still_requires_refresh_after_conflict(client: httpx.AsyncClient) -> None:
    await reset(client, "two-seats")
    initial = (await client.get("/flights/BA456")).json()
    expected_version = initial["version"]

    alice, bob = await asyncio.gather(
        client.post(
            "/flights/BA456/book",
            json={"passenger_name": "alice", "expected_version": expected_version},
        ),
        client.post(
            "/flights/BA456/book",
            json={"passenger_name": "bob", "expected_version": expected_version},
        ),
    )

    statuses = [alice.status_code, bob.status_code]
    assert statuses.count(201) == 1
    assert statuses.count(409) == 1

    flight = (await client.get("/flights/BA456")).json()
    assert flight["remaining_seats"] == 1
    assert flight["bookings_count"] == 1
    assert flight["version"] == 1
