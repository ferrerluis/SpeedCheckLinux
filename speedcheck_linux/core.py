"""Desktop-independent preferences, state, and start-to-start scheduling."""

import json
import math
import os
import tempfile
from pathlib import Path

INTERVALS = (5, 10, 15, 30, 60)
MODES = ("both", "download", "upload")
DEFAULTS = {"interval_minutes": 15, "display_mode": "both", "paused": False,
            "launch_on_login": True}


def mbps(byte_count, elapsed):
    if byte_count <= 0 or elapsed <= 0 or not math.isfinite(elapsed):
        raise ValueError("A measurement needs transferred bytes and positive elapsed time")
    return byte_count * 8 / elapsed / 1_000_000


def read_json(path):
    try:
        value = json.loads(Path(path).read_text())
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temporary = tempfile.mkstemp(prefix=".speedcheck-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            json.dump(value, stream, indent=2, allow_nan=False)
            stream.write("\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def preferences(path):
    saved = read_json(path)
    result = DEFAULTS.copy()
    if saved.get("interval_minutes") in INTERVALS:
        result["interval_minutes"] = saved["interval_minutes"]
    if saved.get("display_mode") in MODES:
        result["display_mode"] = saved["display_mode"]
    for key in ("paused", "launch_on_login"):
        if isinstance(saved.get(key), bool):
            result[key] = saved[key]
    return result


def valid_result(value):
    return isinstance(value, dict) and all(
        isinstance(value.get(key), (int, float)) and
        math.isfinite(value[key]) and value[key] > 0
        for key in ("download", "upload", "finished_at"))


def finish_attempt(state, result=None, error=None, now=0):
    """Commit both directions together; an unsuccessful attempt never replaces them."""
    if result is not None and not valid_result(result):
        error, result = "Invalid or incomplete measurement", None
    if result is not None:
        state["result"] = result
    state["attempt"] = {"finished_at": now, "error": error}


class Schedule:
    def __init__(self, interval=900, due=None, paused=False):
        self.interval = interval
        self.due = due
        self.paused = paused
        self.running = False
        self.last_start = None
        self.retry_at = 0

    def ready(self, now, online=True):
        return (not self.paused and not self.running and online and
                now >= self.retry_at and (self.due is None or now >= self.due))

    def start(self, now, manual=False):
        if self.running or (not manual and not self.ready(now)):
            return False
        self.running = True
        self.last_start = now
        self.due = now + self.interval
        self.retry_at = 0
        return True

    def finish(self, now, failed=False):
        self.running = False
        # Avoid a tight retry loop even if a very short verification interval is used.
        if failed:
            self.retry_at = now + min(60, self.interval)

    def set_interval(self, seconds, now):
        self.interval = seconds
        self.due = (self.last_start if self.last_start is not None else now) + seconds


class Paths:
    def __init__(self):
        home = Path.home()
        self.config = Path(os.getenv("XDG_CONFIG_HOME", home / ".config"))
        self.state_dir = Path(os.getenv("XDG_STATE_HOME", home / ".local/state")) / "speedcheck-linux"
        self.prefs = self.config / "speedcheck-linux/config.json"
        self.state = self.state_dir / "state.json"
        self.status = self.state_dir / "status.json"
        self.autostart = self.config / "autostart/speedcheck-linux.desktop"
