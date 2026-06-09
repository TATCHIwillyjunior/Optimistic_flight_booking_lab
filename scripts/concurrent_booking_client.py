import argparse
import asyncio

import httpx


async def book(
    client: httpx.AsyncClient,
    flight_id: str,
    passenger_name: str,
    expected_version: int,
) -> httpx.Response:
    return await client.post(
        f"/flights/{flight_id}/book",
        json={
            "passenger_name": passenger_name,
            "expected_version": expected_version,
        },
    )


def response_label(response: httpx.Response) -> str:
    reason = response.reason_phrase or ""
    label = f"{response.status_code} {reason}".strip()

    if response.status_code == 409:
        try:
            error = response.json()["detail"]["error"]
        except (KeyError, TypeError, ValueError):
            return label
        return f"{label} {error}"

    return label


async def main(base_url: str, scenario: str, flight_id: str) -> None:
    async with httpx.AsyncClient(base_url=base_url, timeout=10.0) as client:
        await client.post("/admin/reset", json={"scenario": scenario})

        initial = (await client.get(f"/flights/{flight_id}")).json()
        expected_version = initial["version"]

        print("Initial flight:")
        print(
            f"{flight_id} remaining_seats={initial['remaining_seats']} "
            f"version={initial['version']}"
        )
        print()
        print(f"Sending two concurrent requests using expected_version={expected_version}...")
        print()

        alice_response, bob_response = await asyncio.gather(
            book(client, flight_id, "alice", expected_version),
            book(client, flight_id, "bob", expected_version),
        )

        print(f"alice -> {response_label(alice_response)}")
        print(f"bob   -> {response_label(bob_response)}")
        print()

        final = (await client.get(f"/flights/{flight_id}")).json()
        print("Final flight:")
        print(
            f"remaining_seats={final['remaining_seats']} "
            f"version={final['version']} "
            f"bookings_count={final['bookings_count']}"
        )
        print()
        print("Observation:")

        if (
            alice_response.status_code == 201
            and bob_response.status_code == 201
            and final["bookings_count"] > final["total_seats"]
        ):
            print("The invariant was broken: two bookings were confirmed for one seat.")
        elif {alice_response.status_code, bob_response.status_code} == {201, 409}:
            print("One request succeeded. The stale request was rejected and must refresh before retrying.")
            if final["remaining_seats"] > 0:
                print("Seats remain, but this stale request still has to refresh before trying again.")
        else:
            print("Compare the responses with the final flight state and explain what happened.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Send two concurrent booking requests.")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--scenario", choices=["last-seat", "two-seats"], default="last-seat")
    parser.add_argument("--flight-id", default="AF123")
    args = parser.parse_args()

    asyncio.run(main(args.base_url, args.scenario, args.flight_id))
