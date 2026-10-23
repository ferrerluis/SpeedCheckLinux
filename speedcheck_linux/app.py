"""GTK indicator and the application's single scheduler."""

import json
import logging
import math
import multiprocessing
import os
import signal
import sys
import time
from datetime import datetime
from pathlib import Path

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("AyatanaAppIndicator3", "0.1")
from gi.repository import AyatanaAppIndicator3 as Indicator, Gio, GLib, Gtk

from .core import MODES, INTERVALS, Paths, Schedule, finish_attempt, preferences, read_json, valid_result, write_json
from .measurement import TEST_DEADLINE, worker

APP_ID = "io.github.speedchecklinux.SpeedCheckLinux"


def clock_label(timestamp):
    return datetime.fromtimestamp(timestamp).astimezone().strftime("%a %H:%M:%S %Z") if timestamp else "Never"


def number(value):
    return "—" if value is None else (f"{value:.1f}" if value < 10 else f"{value:.0f}")


class SpeedCheck(Gtk.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE)
        self.paths = Paths()
        self.process = None
        self.connection = None
        self.progress = {}
        self.phase = ""
        self.indicator = None
        self.shutting_down = False

    def do_startup(self):
        Gtk.Application.do_startup(self)
        self.hold()
        self.prefs = preferences(self.paths.prefs)
        self.state = read_json(self.paths.state)
        if not valid_result(self.state.get("result")):
            self.state.pop("result", None)
        if not isinstance(self.state.get("attempt"), dict):
            self.state.pop("attempt", None)
        elif not isinstance(self.state["attempt"].get("error"), (str, type(None))):
            self.state.pop("attempt", None)
        due = self.state.get("next_due")
        if not isinstance(due, (int, float)) or not 0 < due < time.time() + 3600:
            due = None
        self.schedule = Schedule(self.prefs["interval_minutes"] * 60, due, self.prefs["paused"])
        last_start = self.state.get("last_start")
        if isinstance(last_start, (int, float)) and math.isfinite(last_start) and 0 < last_start <= time.time():
            self.schedule.last_start = last_start
        self.monitor = Gio.NetworkMonitor.get_default()
        # NETWORK_AVAILABLE means a route exists. Captive portals/errors are handled by HTTPS.
        self.make_menu()
        # AppIndicator requires an icon; the GNOME helper removes its allocation.
        # Keep the desktop-launcher gauge separate from the text-only panel display.
        icon = str(Path(__file__).resolve().parent.parent / "assets/panel-empty.svg")
        self.indicator = Indicator.Indicator.new("speedcheck-linux", icon, Indicator.IndicatorCategory.APPLICATION_STATUS)
        self.indicator.set_title("SpeedCheck Linux")
        self.indicator.set_menu(self.menu)
        self.indicator.set_status(Indicator.IndicatorStatus.ACTIVE)
        try:
            self.set_autostart(self.prefs["launch_on_login"])
        except OSError:
            logging.exception("Cannot update login startup")
        self.tick_id = GLib.timeout_add(100, self.tick)
        GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGTERM, self.request_quit)
        GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGINT, self.request_quit)
        self.refresh()

    def make_menu(self):
        self.menu = Gtk.Menu()
        self.rows = {}
        for key, label in (("title", "SpeedCheck Linux · Cloudflare"), ("download", ""),
                           ("upload", ""), ("last", ""), ("next", ""), ("status", "")):
            item = Gtk.MenuItem(label=label)
            item.set_sensitive(False)
            self.rows[key] = item
            self.menu.append(item)
        self.menu.append(Gtk.SeparatorMenuItem())
        self.test_item = self.add_action("Test Now", lambda *_: self.start_test(manual=True))
        self.pause_item = self.add_action("Pause automatic testing", lambda *_: self.set_paused(not self.schedule.paused))
        self.interval_items = self.add_radios("Automatic testing interval", [(x, f"{x} minutes") for x in INTERVALS],
                                              self.prefs["interval_minutes"], self.set_interval)
        self.display_items = self.add_radios("Panel display", [("both", "Download and upload"),
                                            ("download", "Download only"), ("upload", "Upload only")],
                                             self.prefs["display_mode"], self.set_display)
        self.login_item = Gtk.CheckMenuItem(label="Launch on login")
        self.login_item.set_active(self.prefs["launch_on_login"])
        self.login_item.connect("toggled", lambda item: self.set_autostart(item.get_active()))
        self.menu.append(self.login_item)
        self.menu.append(Gtk.SeparatorMenuItem())
        self.add_action("Quit", lambda *_: self.request_quit())
        self.menu.show_all()

    def add_action(self, label, callback):
        item = Gtk.MenuItem(label=label)
        item.connect("activate", callback)
        self.menu.append(item)
        return item

    def add_radios(self, label, choices, selected, callback):
        root = Gtk.MenuItem(label=label)
        submenu = Gtk.Menu()
        root.set_submenu(submenu)
        self.menu.append(root)
        items, group = {}, None
        for value, text in choices:
            item = Gtk.RadioMenuItem.new_with_label(group, text)
            group = item.get_group()
            item.set_active(value == selected)
            item.connect("toggled", lambda widget, choice=value: callback(choice) if widget.get_active() else None)
            submenu.append(item)
            items[value] = item
        return items

    def save(self):
        self.state["next_due"] = self.schedule.due
        write_json(self.paths.prefs, self.prefs)
        write_json(self.paths.state, self.state)

    def set_interval(self, minutes):
        self.prefs["interval_minutes"] = minutes
        self.schedule.set_interval(minutes * 60, time.time())
        self.interval_items[minutes].set_active(True)
        self.save()
        self.refresh()

    def set_display(self, mode):
        self.prefs["display_mode"] = mode
        self.display_items[mode].set_active(True)
        self.save()
        self.refresh()

    def set_paused(self, paused):
        self.prefs["paused"] = self.schedule.paused = paused
        self.save()
        self.refresh()

    def set_autostart(self, enabled):
        executable = Path.home() / ".local/bin/speedcheck-linux"
        if enabled:
            self.paths.autostart.parent.mkdir(parents=True, exist_ok=True)
            # Desktop entry quoting follows the Desktop Entry spec, not shell quoting.
            quoted = str(executable).replace("\\", "\\\\").replace('"', '\\"').replace("`", "\\`").replace("$", "\\$")
            self.paths.autostart.write_text(
                '[Desktop Entry]\nType=Application\nName=SpeedCheck Linux\n'
                f'Exec="{quoted}"\nTryExec={executable}\nIcon=speedcheck-linux\n'
                'Terminal=false\nX-GNOME-Autostart-enabled=true\nStartupNotify=false\n')
        else:
            self.paths.autostart.unlink(missing_ok=True)
        self.prefs["launch_on_login"] = enabled
        if self.login_item.get_active() != enabled:
            self.login_item.set_active(enabled)
        self.save()

    def start_test(self, manual=False):
        now = time.time()
        if not self.schedule.start(now, manual):
            return False
        self.progress = {}
        self.phase = "Starting test…"
        self.started_monotonic = time.monotonic()
        self.started_wall = now
        parent, child = multiprocessing.get_context("spawn").Pipe(duplex=False)
        self.connection = parent
        self.process = multiprocessing.get_context("spawn").Process(target=worker, args=(child,), daemon=True)
        try:
            self.process.start()
        except Exception as error:
            child.close()
            self.complete(error=f"Cannot start measurement: {error}")
            return False
        child.close()
        self.state["last_start"] = now
        self.save()
        logging.info("Test started; next due %s", clock_label(self.schedule.due))
        self.refresh()
        return True

    def stop_worker(self):
        if self.process and self.process.pid:
            if self.process.is_alive():
                self.process.kill()  # Includes DNS stalls and a blocked upload write.
            self.process.join(timeout=0.1)
            if not self.process.is_alive():
                self.process.close()
        self.process = None
        if self.connection:
            self.connection.close()
            self.connection = None

    def complete(self, result=None, error=None):
        self.stop_worker()
        finish_attempt(self.state, result, error, time.time())
        self.schedule.finish(time.time(), failed=bool(self.state["attempt"]["error"]))
        self.progress = {}
        self.phase = ""
        self.save()
        logging.info("Test finished: %s", self.state["attempt"])
        self.refresh()

    def tick(self):
        if self.shutting_down:
            return False
        if self.process:
            try:
                while self.connection.poll():
                    event = self.connection.recv()
                    if event["type"] == "progress":
                        self.progress[event["direction"]] = event["value"]
                    elif event["type"] == "phase":
                        self.phase = "Testing " + event["direction"] + "…"
                    elif event["type"] in ("result", "error"):
                        self.complete(result=event.get("result"), error=event.get("error"))
                        break
            except (EOFError, OSError):
                if self.process:
                    self.complete(error="Measurement worker stopped unexpectedly")
            if self.process and (time.monotonic() - self.started_monotonic >= TEST_DEADLINE or
                                 time.time() - self.started_wall >= TEST_DEADLINE):
                self.complete(error=f"Test timed out after {TEST_DEADLINE} seconds")
        if self.schedule.ready(time.time(), self.monitor.get_network_available()):
            self.start_test()
        self.refresh()
        return True

    def refresh(self):
        if not self.indicator:
            return
        result = self.state.get("result", {})
        values = {key: self.progress.get(key, result.get(key)) for key in ("download", "upload")}
        parts = []
        if self.prefs["display_mode"] in ("both", "download"):
            parts.append("↓ " + number(values["download"]))
        if self.prefs["display_mode"] in ("both", "upload"):
            parts.append("↑ " + number(values["upload"]))
        error = self.state.get("attempt", {}).get("error")
        stale = bool(result) and time.time() - result["finished_at"] > self.schedule.interval * 2
        suffix = " ···" if self.schedule.running else (" *" if error or stale else "")
        label = " ".join(parts) + " Mbps" + suffix
        self.indicator.set_label(label, "↓ 9999 ↑ 9999 Mbps")
        self.rows["download"].set_label("Download: " + number(values["download"]) + " Mbps")
        self.rows["upload"].set_label("Upload: " + number(values["upload"]) + " Mbps")
        self.rows["last"].set_label("Last successful test: " + clock_label(result.get("finished_at")))
        next_text = "Paused" if self.schedule.paused else clock_label(self.schedule.due)
        self.rows["next"].set_label("Next test: " + next_text)
        status = self.phase or ("Last attempt failed: " + error if error else
                               ("Results are stale" if stale else "Ready"))
        if not self.monitor.get_network_available():
            status = "Offline · waiting for connectivity"
        self.rows["status"].set_label(status)
        self.test_item.set_sensitive(not self.schedule.running)
        self.pause_item.set_label("Resume automatic testing" if self.schedule.paused else "Pause automatic testing")
        snapshot = {"pid": os.getpid(), "worker_pid": self.process.pid if self.process else None,
                    "running": self.schedule.running, "label": label, "status": status,
                    "preferences": self.prefs, "effective_interval_seconds": self.schedule.interval,
                    "next_due": self.schedule.due, "next_test": next_text, "result": result,
                    "attempt": self.state.get("attempt"), "online": self.monitor.get_network_available()}
        # UI updates are cheap; disk writes happen only when displayed state changes.
        serialized = json.dumps(snapshot, sort_keys=True)
        if serialized != getattr(self, "last_snapshot", None):
            write_json(self.paths.status, snapshot)
            self.last_snapshot = serialized

    def do_command_line(self, command_line):
        args = command_line.get_arguments()[1:]
        try:
            if not args:
                self.refresh()
            elif args == ["--status"]:
                command_line.print_literal(json.dumps(read_json(self.paths.status), indent=2) + "\n")
            elif args == ["--test-now"]:
                self.start_test(manual=True)
            elif args == ["--pause"]:
                self.set_paused(True)
            elif args == ["--resume"]:
                self.set_paused(False)
            elif args == ["--quit"]:
                self.request_quit()
            elif len(args) == 2 and args[0] == "--interval" and int(args[1]) in INTERVALS:
                self.set_interval(int(args[1]))
            elif len(args) == 2 and args[0] == "--display-mode" and args[1] in MODES:
                self.set_display(args[1])
            elif len(args) == 2 and args[0] == "--launch-on-login" and args[1] in ("on", "off"):
                self.set_autostart(args[1] == "on")
            elif len(args) == 2 and args[0] == "--verification-interval" and 2 <= int(args[1]) <= 60:
                # Temporary, never persisted. --interval 15 restores normal operation.
                self.schedule.set_interval(int(args[1]), time.time())
                self.refresh()
            else:
                raise ValueError("Unknown command or unsupported value")
        except (ValueError, OSError) as error:
            command_line.printerr_literal(str(error) + "\n")
            return 2
        return 0

    def request_quit(self):
        self.shutting_down = True
        self.stop_worker()
        self.schedule.running = False
        self.save()
        self.indicator.set_status(Indicator.IndicatorStatus.PASSIVE)
        self.quit()
        return False


def main():
    paths = Paths()
    paths.state_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    logging.basicConfig(filename=paths.state_dir / "app.log", level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    # Keep the diagnostic log bounded without adding background machinery.
    log_path = paths.state_dir / "app.log"
    if log_path.stat().st_size > 1_000_000:
        log_path.write_text("")
    # GTK consumes --display as its own display-server option before dispatch.
    # Normalize our legacy spelling locally; --display-mode is unambiguous.
    args = ["--display-mode" if arg == "--display" else arg for arg in sys.argv]
    return SpeedCheck().run(args)
