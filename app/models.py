from typing import Literal

from pydantic import BaseModel


class FlightRead(BaseModel):
    flight_id: str
    total_seats: int
    remaining_seats: int
    version: int
    bookings_count: int


class BookingRequest(BaseModel):
    passenger_name: str
    expected_version: int | None = None


class BookingRead(BaseModel):
    booking_id: str
    flight_id: str
    passenger_name: str
    status: str
    flight_version: int
    remaining_seats: int


class ResetRequest(BaseModel):
    scenario: Literal["last-seat", "two-seats"] = "last-seat"
