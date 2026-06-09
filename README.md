# Optimistic Concurrency Lab - Flight Booking with Version Numbers

Approximate duration: 40 minutes

## Goal

You will run a deliberately unsafe flight-booking service, reproduce a concurrency bug, and then make the booking operation use optimistic concurrency.

By the end of the activity, you should be able to explain:

- optimistic concurrency;
- resource version numbers;
- stale reads;
- conflict detection;
- `409 Conflict`;
- why retries must refresh state;
- why versioning is different from locking;
- why this in-memory lab is a teaching model, not a production-grade storage solution.

## Background

A client reads a resource. The resource has a `version`. When the client requests a change, it sends the version it observed. The server accepts the change only if the resource is still compatible with that observation.

If the resource changed, the server returns `409 Conflict`. The client must refresh the resource and decide whether to retry.

Example:

```text
1. Alice reads flight AF123: remaining_seats = 1, version = 0.
2. Bob reads the same flight: remaining_seats = 1, version = 0.
3. Alice books with expected_version = 0.
4. The flight becomes version = 1.
5. Bob books with expected_version = 0.
6. Bob's request is stale, so the server returns 409 Conflict.
```

## Rules

For this activity, you are not allowed to use:

- locks;
- semaphores;
- queues;
- a database;
- transactions;
- a single global lock;
- a background worker that serializes all bookings.

Your task is to implement optimistic concurrency using the flight version number.

## Setup

Use Docker Compose for this lab. The same commands work on macOS, Linux, and Windows with Docker Desktop or Docker Engine.

Build the image:

```bash
docker compose build
```

Start the API:

```bash
docker compose up api
```

The API documentation is available at:

```text
http://localhost:8000/docs
```

If port `8000` is already used on your machine, choose another host port:

```bash
API_PORT=8001 docker compose up api
```

On Windows PowerShell:

```powershell
$env:API_PORT=8001; docker compose up api
```

Then open:

```text
http://localhost:8001/docs
```

Use the same `API_PORT=8001` prefix on later `docker compose` commands that depend on the running API, for example:

```bash
API_PORT=8001 docker compose run --rm client
```

On Windows PowerShell:

```powershell
$env:API_PORT=8001; docker compose run --rm client
```

The Docker and Uvicorn commands run one Uvicorn worker only.

When you change the server code, stop the API with `Ctrl+C` and start it again:

```bash
docker compose up api
```

## Run the Unsafe Demo

In another terminal:

```bash
docker compose run --rm client
```

Before you fix the code, two concurrent clients can both confirm the last seat on `AF123`.

Example before versioning is implemented:

```text
Initial flight:
AF123 remaining_seats=1 version=0

Sending two concurrent requests using expected_version=0...

alice -> 201 Created
bob   -> 201 Created

Final flight:
remaining_seats=0 version=0 bookings_count=2

Observation:
The invariant was broken: two bookings were confirmed for one seat.
```

Before changing the code, answer these two questions:

1. Which value did both clients observe before sending their booking request?
> *My answer: Each client saw the remainninng booking seat the version.*
2. Which final state proves that the service accepted an impossible result?
> *My answer: The fact that both client recieved a 201 created when 1 remaining seat is available also the fact that there was no change over the version considering two booking has been made.*

## Your Task

Make the booking endpoint behave as an optimistic concurrency API.

The externally visible contract is:

- `GET /flights/{flight_id}` exposes the current flight version.
- A booking request must include the version observed by the client.
- A confirmed booking consumes one seat, records one booking, and advances the flight version exactly once.
- A request based on stale flight state returns `409 Conflict` with error `VERSION_CONFLICT`.
- A failed request does not change `remaining_seats`, `bookings_count`, or `version`.
- Two concurrent booking requests based on the same observation cannot both modify the same flight.
- The solution remains lock-free and does not use a database, transaction, queue, or background worker.

Do not search for TODO comments as the main strategy. Use the API behavior, the code structure, and the tests to identify where the decision should happen.

## Checkpoints

After your fix, rerun the last-seat demo:

```bash
docker compose run --rm client
```

Expected shape:

```text
alice -> 201 Created
bob   -> 409 Conflict VERSION_CONFLICT

Final flight:
remaining_seats=0 version=1 bookings_count=1
```

Then run the two-seat scenario:

```bash
docker compose run --rm client python scripts/concurrent_booking_client.py --base-url http://api:8000 --scenario two-seats --flight-id BA456
```

Expected shape:

```text
alice -> 201 Created
bob   -> 409 Conflict VERSION_CONFLICT

Final flight:
remaining_seats=1 version=1 bookings_count=1
```

This second scenario is important: one seat remains, but the stale request is still rejected. The client must refresh before deciding whether another booking attempt is valid.

## Tests

Run:

```bash
docker compose run --rm tests
```

Some tests fail in the starter version. That is intentional: they describe the target API contract after optimistic concurrency is implemented.

## If You Are Stuck

Open these hints gradually.

Hint 1:
The version belongs to the flight resource. It is not a booking identifier.

Hint 2:
A stale request is not the same as a sold-out request. The error should explain which situation happened.

Hint 3:
Think carefully about when the service learns whether the request is stale. Checking too early can preserve the race.

Hint 4:
Once the final decision to accept a booking has been made, avoid adding another `await` before the state update is finished.

Hint 5:
A `409` response means the client must refresh the flight before deciding whether to retry.

## Resetting State

The app includes a classroom reset endpoint:

```http
POST /admin/reset
```

Request body:

```json
{
  "scenario": "last-seat"
}
```

Supported scenarios:

- `last-seat`: resets `AF123` to one available seat.
- `two-seats`: resets `BA456` to two available seats.

Both scenarios reset all bookings and all versions to `0`.

## Useful Docker Commands

Start the API:

```bash
docker compose up api
```

Run the concurrent demo:

```bash
docker compose run --rm client
```

Run the tests:

```bash
docker compose run --rm tests
```

Stop containers and clean up:

```bash
docker compose down
```

Rebuild after dependency changes:

```bash
docker compose build
```

## Optional Local Python Workflow

Docker is the recommended classroom workflow. If your instructor asks you to run the project without Docker, use:

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Reflection Questions

1. Why did the second request become stale?
> *My answer: It's because the second request was reading old data or version since both request was made at the same moment, the first request will be executed and then there will be a version change which now update the version of the page and since the second request was made base on the old vrsioning, it request won't go throught as the old version isn't the same as the new one*
2. Why is `409 Conflict` more appropriate than `500 Internal Server Error`?
> *My answer: 500 Internal Server Conflict here will be telling us our backend or server has crashed or an exception was thrown that we didn't handle which for our case is not throught as 409 Conflict is a better way to say to the client or user to refresh your page since your request is valid and your server is running perfectly find*
3. What should a real client do after receiving `VERSION_CONFLICT`?
> *My answer: Refresh his page*
4. Why can the two-seat scenario reject a request even though a seat remains?
*My answer: Even though there are 2 seat remaining as long as 2 request are done at the same moment, one will be executed and the other will not due to version change or because it enter a slate state*
5. What would go wrong if the version check happened before simulated business work or network delay?
*My answer: you will find your self with version = 2 since both request went through without raising the VersionConflict when the client's expected_version does not match the current flight version*
6. What would happen if this app ran with two separate processes and in-memory state?
*My answer: each process will have thier own memory since the can't see each order changes(i.e versioning) therefore dublicated will be created over a single seat and that moment*
7. In a production system, where should the version check and update happen?
*My answer: In the database as putting in constraint will affect rows to detect conflicts*

## Important Caveat

This lab uses in-memory state to make the idea visible. In production, optimistic concurrency is usually enforced by a shared storage system, such as a database, using an atomic conditional update. We will connect this idea to transactions and database constraints in the next class.
