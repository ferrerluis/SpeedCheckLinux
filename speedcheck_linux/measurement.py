"""Bounded, sequential Cloudflare transfers. Invoked in an expendable process."""

import time
import uuid

import requests

from .core import mbps

BASE = "https://speed.cloudflare.com"
TEST_DEADLINE = 60
PHASE_BUDGET = 24
TIMEOUT = (4, 4)  # connect and socket inactivity; parent also enforces a hard deadline
CHUNK = 64 * 1024


class MeasurementError(Exception):
    pass


def transfer(session, direction, size, deadline, progress):
    count = 0
    last_emit = 0
    started = time.monotonic()

    def check():
        if time.monotonic() >= deadline:
            raise MeasurementError("Test deadline exceeded")

    check()
    if direction == "download":
        with session.get(BASE + "/__down", params={"bytes": size, "nonce": uuid.uuid4().hex},
                         stream=True, timeout=TIMEOUT, allow_redirects=False) as response:
            if response.status_code != 200:
                raise MeasurementError(f"Download returned HTTP {response.status_code}")
            if response.headers.get("Content-Encoding", "identity") != "identity":
                raise MeasurementError("Unexpected compressed response")
            # Include every body byte, timed from before reading it, not after the first chunk.
            started = time.monotonic()
            for chunk in response.iter_content(CHUNK):
                check()
                count += len(chunk)
                if count > size:
                    raise MeasurementError("Download exceeded requested size")
                now = time.monotonic()
                if now - last_emit >= 0.2 and now > started:
                    progress(mbps(count, now - started))
                    last_emit = now
    else:
        class Body:
            def __len__(self):
                return size

            def __iter__(self):
                nonlocal count, last_emit
                block = bytes(CHUNK)
                while count < size:
                    check()
                    piece = block[:min(CHUNK, size - count)]
                    yield piece
                    count += len(piece)
                    now = time.monotonic()
                    if now - last_emit >= 0.2:
                        # Provisional upload includes client buffering; final value waits for ACK.
                        progress(mbps(count, now - started))
                        last_emit = now

        with session.post(BASE + "/__up", data=Body(), timeout=TIMEOUT,
                          headers={"Content-Type": "application/octet-stream"},
                          stream=True, allow_redirects=False) as response:
            if response.status_code != 200:
                raise MeasurementError(f"Upload returned HTTP {response.status_code}")
            # Bound response bytes as well; the successful response acknowledges the full POST.
            response_count = 0
            for chunk in response.iter_content(CHUNK):
                check()
                response_count += len(chunk)
                if response_count > 1_000_000:
                    raise MeasurementError("Unexpected upload response size")
    check()
    elapsed = time.monotonic() - started
    if count != size:
        raise MeasurementError(f"Incomplete {direction}: {count} of {size} bytes")
    return count, elapsed


def measure(emit):
    deadline = time.monotonic() + TEST_DEADLINE - 1
    results = {}
    with requests.Session() as session:
        session.headers.update({"Accept-Encoding": "identity", "Cache-Control": "no-store",
                                "User-Agent": "SpeedCheckLinux/1.0"})
        for direction, first, maximum in (("download", 1_000_000, 64_000_000),
                                          ("upload", 256_000, 32_000_000)):
            emit({"type": "phase", "direction": direction})
            phase_deadline = min(deadline, time.monotonic() + PHASE_BUDGET)
            # Small warm-up opens TLS and helps avoid measuring only a cold connection.
            transfer(session, direction, 64_000, phase_deadline, lambda value: None)
            total_bytes, total_seconds, size = 0, 0, first
            for _ in range(3):
                count, elapsed = transfer(
                    session, direction, size, phase_deadline,
                    lambda value: emit({"type": "progress", "direction": direction, "value": value}))
                total_bytes += count
                total_seconds += elapsed
                value = mbps(total_bytes, total_seconds)
                emit({"type": "progress", "direction": direction, "value": value})
                # Target ~1.5 seconds per sample, but cap allocation and data use.
                size = max(first, min(maximum, int(count / elapsed * 1.5)))
            results[direction] = value
            results[direction + "_bytes"] = total_bytes + 64_000
            results[direction + "_seconds"] = total_seconds
    results["finished_at"] = time.time()
    return results


def worker(connection):
    try:
        result = measure(connection.send)
        connection.send({"type": "result", "result": result})
    except Exception as error:
        connection.send({"type": "error", "error": f"{type(error).__name__}: {error}"[:300]})
    finally:
        connection.close()
