import unittest
from unittest.mock import patch

import requests

from speedcheck_linux.measurement import MeasurementError, measure, sustained_download, transfer


class Response:
    status_code = 200
    headers = {}

    def __init__(self, chunks):
        self.chunks = chunks

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def iter_content(self, size):
        yield from self.chunks


class Session:
    def __init__(self, chunks):
        self.response = Response(chunks)
        self.sent = 0

    def get(self, *args, **kwargs):
        return self.response

    def post(self, *args, data, **kwargs):
        self.sent = sum(map(len, data))
        return self.response


class TransferTests(unittest.TestCase):
    def test_counts_real_download_bytes_and_rejects_partial_or_oversized_body(self):
        count, seconds = transfer(Session([b"abc", b"de"]), "download", 5, float("inf"), lambda v: None)
        self.assertEqual(count, 5)
        self.assertGreater(seconds, 0)
        for chunks in ([b"abc"], [b"abcdef"]):
            with self.assertRaises(MeasurementError):
                transfer(Session(chunks), "download", 5, float("inf"), lambda v: None)

    def test_upload_waits_for_acknowledgement_and_counts_exact_body(self):
        session = Session([b"OK"])
        count, _ = transfer(session, "upload", 100_001, float("inf"), lambda v: None)
        self.assertEqual(session.sent, 100_001)
        self.assertEqual(count, 100_001)

    def test_deadline_and_http_error(self):
        with self.assertRaises(MeasurementError):
            transfer(Session([]), "download", 1, 0, lambda v: None)
        session = Session([b"a"])
        session.response.status_code = 503
        with self.assertRaises(MeasurementError):
            transfer(session, "download", 1, float("inf"), lambda v: None)

    def test_connection_read_timeout_propagates(self):
        session = Session([])
        with patch.object(session, "get", side_effect=requests.Timeout("stalled")):
            with self.assertRaises(requests.Timeout):
                transfer(session, "download", 1, float("inf"), lambda v: None)

    def test_fast_connection_adapts_payloads_without_exceeding_caps(self):
        calls = []

        def fast_transfer(session, direction, size, deadline, progress):
            calls.append((direction, size))
            return size, size / 250_000_000  # Simulated 2 Gbps without allocation/network.

        with patch("speedcheck_linux.measurement.transfer", side_effect=fast_transfer):
            result = measure(lambda event: None)
        self.assertAlmostEqual(result["download"], 2000)
        self.assertAlmostEqual(result["upload"], 2000)
        self.assertLessEqual(result["download_bytes"], 105_064_000)
        self.assertLessEqual(result["upload_bytes"], 64_320_000)
        self.assertIn(("download", 64_000_000), calls)
        self.assertIn(("upload", 32_000_000), calls)

    def test_short_probe_does_not_trap_a_fast_link_in_small_samples(self):
        samples = []

        def slow_start(session, direction, size, deadline, progress):
            # Short payloads look slow even though longer transfers reach 200 Mbps.
            rate = 25_000_000 if size >= 16_000_000 else 3_000_000
            samples.append(size)
            return size, size / rate

        with patch("speedcheck_linux.measurement.transfer", side_effect=slow_start):
            value, total, measured, seconds = sustained_download(None, float("inf"), lambda v: None)
        self.assertGreaterEqual(measured, 32_000_000)
        self.assertAlmostEqual(value, 200)
        self.assertEqual(total, sum(samples))
        self.assertAlmostEqual(value, measured * 8 / seconds / 1_000_000)

    def test_final_sustained_sample_is_used_even_if_an_earlier_sample_was_faster(self):
        def changing_link(session, direction, size, deadline, progress):
            rate = 12_500_000 if size >= 32_000_000 else 25_000_000
            return size, size / rate

        with patch("speedcheck_linux.measurement.transfer", side_effect=changing_link):
            value, _, measured, _ = sustained_download(None, float("inf"), lambda v: None)
        self.assertGreaterEqual(measured, 32_000_000)
        self.assertAlmostEqual(value, 100)  # Not the earlier 200 Mbps peak.

    def test_slow_link_and_limited_remaining_budget_do_not_force_large_payloads(self):
        requested = []
        now = [0.0]

        def slow_transfer(session, direction, size, deadline, progress):
            requested.append(size)
            seconds = size / 62_500  # 0.5 Mbps: one 1 MB sample takes 16 seconds.
            now[0] += seconds
            self.assertLess(now[0], deadline)
            return size, seconds

        with patch("speedcheck_linux.measurement.transfer", side_effect=slow_transfer), \
             patch("speedcheck_linux.measurement.time.monotonic", side_effect=lambda: now[0]):
            value, _, _, _ = sustained_download(None, 24, lambda v: None)
        self.assertEqual(requested, [1_000_000])
        self.assertAlmostEqual(value, .5)

        # A quicker probe near the budget boundary must still leave timeout room.
        now[0] = 18
        requested.clear()
        with patch("speedcheck_linux.measurement.transfer", return_value=(1_000_000, 1)), \
             patch("speedcheck_linux.measurement.time.monotonic", side_effect=lambda: now[0]):
            value, total, measured, seconds = sustained_download(None, 22, lambda v: None)
        self.assertEqual(total, 1_000_000)
        self.assertEqual(measured, 1_000_000)
        self.assertEqual(seconds, 1)
