import json
import tempfile
import unittest
from pathlib import Path

from speedcheck_linux.core import Schedule, finish_attempt, mbps, preferences, read_json, write_json


class ConversionTests(unittest.TestCase):
    def test_decimal_mbps_on_fast_and_slow_connections(self):
        self.assertEqual(mbps(125_000_000, 1), 1000)
        self.assertEqual(mbps(1_000_000, 2), 4)
        self.assertAlmostEqual(mbps(64_000_000, 0.2), 2560)

    def test_invalid_measurement_is_rejected(self):
        for count, duration in ((0, 1), (1, 0), (1, -1), (1, float("inf"))):
            with self.assertRaises(ValueError):
                mbps(count, duration)


class SchedulingTests(unittest.TestCase):
    def test_start_cadence_manual_reset_and_overlap(self):
        schedule = Schedule()
        self.assertTrue(schedule.start(100))
        self.assertEqual(schedule.due, 1000)
        self.assertFalse(schedule.start(110, manual=True))
        schedule.finish(130)
        self.assertFalse(schedule.ready(999))
        self.assertTrue(schedule.start(600, manual=True))
        self.assertEqual(schedule.due, 1500)

    def test_suspend_offline_restart_catch_up_only_once(self):
        schedule = Schedule(due=1000)
        self.assertFalse(schedule.ready(10_000, online=False))
        self.assertTrue(schedule.start(10_000))
        self.assertEqual(schedule.due, 10_900)
        schedule.finish(10_030)
        self.assertFalse(schedule.ready(10_030))

    def test_pause_manual_test_and_resume(self):
        schedule = Schedule(paused=True)
        self.assertFalse(schedule.start(100))
        self.assertTrue(schedule.start(100, manual=True))
        schedule.finish(120)
        self.assertFalse(schedule.ready(2000))
        schedule.paused = False
        self.assertTrue(schedule.ready(2000))

    def test_interval_change_and_failed_future_test(self):
        schedule = Schedule()
        schedule.start(100)
        schedule.finish(130, failed=True)
        self.assertEqual(schedule.due, 1000)
        self.assertFalse(schedule.ready(150))
        self.assertTrue(schedule.ready(1000))
        schedule.set_interval(300, 200)
        self.assertEqual(schedule.due, 400)


class PersistenceAndFailureTests(unittest.TestCase):
    def setUp(self):
        self.result = {"download": 240, "upload": 35, "finished_at": 100}

    def test_error_and_partial_result_preserve_last_success(self):
        state = {"result": self.result.copy()}
        finish_attempt(state, error="Timeout", now=200)
        self.assertEqual(state["result"], self.result)
        self.assertEqual(state["attempt"], {"finished_at": 200, "error": "Timeout"})
        finish_attempt(state, result={"download": 1}, now=300)
        self.assertEqual(state["result"], self.result)
        self.assertIn("Invalid", state["attempt"]["error"])

    def test_success_replaces_both_and_clears_failure(self):
        state = {"attempt": {"error": "Timeout"}}
        finish_attempt(state, result=self.result, now=101)
        self.assertEqual(state["result"], self.result)
        self.assertIsNone(state["attempt"]["error"])

    def test_atomic_round_trip_and_corrupt_preferences(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            write_json(path, {"interval_minutes": 30, "display_mode": "upload", "paused": True})
            self.assertEqual(preferences(path)["interval_minutes"], 30)
            self.assertEqual(preferences(path)["display_mode"], "upload")
            path.write_text('{"interval_minutes": -2, "display_mode": "bad", "paused": "yes"}')
            self.assertEqual(preferences(path)["interval_minutes"], 15)
            self.assertFalse(preferences(path)["paused"])
            path.write_text("broken")
            self.assertEqual(read_json(path), {})


if __name__ == "__main__":
    unittest.main()
