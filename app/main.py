from fastapi import FastAPI, HTTPException, status

from app.models import BookingRead, BookingRequest, FlightRead, ResetRequest
from app.store import Flight, FlightNotFound, SoldOut, VersionConflict, store


app = FastAPI(title="Optimistic Flight Booking Lab")


def flight_to_read(flight: Flight) -> FlightRead:
    return FlightRead(
        flight_id=flight.flight_id,
        total_seats=flight.total_seats,
        remaining_seats=flight.remaining_seats,
        version=flight.version,
        bookings_count=len(flight.bookings),
    )


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/flights", response_model=list[FlightRead])
async def list_flights() -> list[FlightRead]:
    return [flight_to_read(flight) for flight in store.list_flights()]


@app.get("/flights/{flight_id}", response_model=FlightRead)
async def get_flight(flight_id: str) -> FlightRead:
    flight = store.get_flight(flight_id)
    if flight is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Flight not found")

    return flight_to_read(flight)


@app.post(
    "/flights/{flight_id}/book",
    response_model=BookingRead,
    status_code=status.HTTP_201_CREATED,
)
async def book_flight(flight_id: str, request: BookingRequest) -> BookingRead:
    try:
        result = await store.book_flight(
            flight_id=flight_id,
            passenger_name=request.passenger_name,
            expected_version=request.expected_version,
        )
    except FlightNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Flight not found")
    except VersionConflict as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "VERSION_CONFLICT",
                "message": "The flight has changed. Refresh the flight and retry with the current version.",
                "current_version": error.current_version,
            },
        )
    except SoldOut as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "SOLD_OUT",
                "message": "No seats left on this flight.",
                "current_version": error.current_version,
            },
        )

    return BookingRead(
        booking_id=result.booking.booking_id,
        flight_id=result.booking.flight_id,
        passenger_name=result.booking.passenger_name,
        status="confirmed",
        flight_version=result.flight_version,
        remaining_seats=result.remaining_seats,
    )


@app.post("/admin/reset")
async def reset_state(request: ResetRequest) -> dict[str, str]:
    store.reset(request.scenario)
    return {"status": "reset", "scenario": request.scenario}
