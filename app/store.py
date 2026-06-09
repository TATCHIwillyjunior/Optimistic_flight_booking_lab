import asyncio
from dataclasses import dataclass, field
from uuid import uuid4


@dataclass
class Booking:
    booking_id: str
    flight_id: str
    passenger_name: str


@dataclass
class Flight:
    flight_id: str
    total_seats: int
    remaining_seats: int
    version: int = 0
    bookings: list[Booking] = field(default_factory=list)


@dataclass
class BookingResult:
    booking: Booking
    flight_version: int
    remaining_seats: int


class FlightNotFound(Exception):
    pass


class VersionConflict(Exception):
    def __init__(self, current_version: int):
        self.current_version = current_version


class SoldOut(Exception):
    def __init__(self, current_version: int):
        self.current_version = current_version


class FlightStore:
    def __init__(self) -> None:
        self._flights: dict[str, Flight] = {}
        self.reset("last-seat")

    def reset(self, scenario: str) -> None:
        self._flights = {
            "AF123": Flight(
                flight_id="AF123",
                total_seats=1,
                remaining_seats=1,
                version=0,
            ),
            "BA456": Flight(
                flight_id="BA456",
                total_seats=2,
                remaining_seats=2,
                version=0,
            ),
        }

        if scenario == "last-seat":
            return
        if scenario == "two-seats":
            return

        raise ValueError(f"Unknown reset scenario: {scenario}")

    def list_flights(self) -> list[Flight]:
        return list(self._flights.values())

    def get_flight(self, flight_id: str) -> Flight | None:
        return self._flights.get(flight_id)

    async def book_flight(
        self,
        flight_id: str,
        passenger_name: str,
        expected_version: int | None,
    ) -> BookingResult:
        flight = self.get_flight(flight_id)
        if flight is None:
            raise FlightNotFound

        observed_remaining_seats = flight.remaining_seats

        # Simulate business work or network delay.
        await asyncio.sleep(0.05)

        if observed_remaining_seats <= 0:
            raise SoldOut(current_version=flight.version)

        booking = Booking(
            booking_id=str(uuid4()),
            flight_id=flight.flight_id,
            passenger_name=passenger_name,
        )

        flight.remaining_seats = max(0, flight.remaining_seats - 1)
        flight.bookings.append(booking)

        return BookingResult(
            booking=booking,
            flight_version=flight.version,
            remaining_seats=flight.remaining_seats,
        )


store = FlightStore()
