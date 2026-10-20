import unittest
from unittest.mock import patch

import requests

from speedcheck_linux.measurement import MeasurementError, measure, transfer


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
        self.assertLessEqual(result["download_bytes"], 129_064_000)
        self.assertLessEqual(result["upload_bytes"], 64_320_000)
        self.assertIn(("download", 64_000_000), calls)
        self.assertIn(("upload", 32_000_000), calls)
