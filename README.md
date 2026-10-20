# SpeedCheck Linux

A small Ubuntu panel app that actively measures internet download and upload speed
with Cloudflare. Both readings stay in the top-right panel between tests:
`↓ 240 ↑ 35 Mbps`. Original Python code and gauge icon; MIT licensed.

## Setup

Requires Ubuntu Desktop, Python 3, GTK3/PyGObject, Requests, and an enabled
AppIndicator extension. Use Ubuntu's Python, not a pip virtual environment:

```sh
sudo apt install python3-gi python3-requests gir1.2-gtk-3.0 gir1.2-ayatanaappindicator3-0.1
git clone https://github.com/ferrerluis/SpeedCheckLinux.git
cd SpeedCheckLinux
./install.sh
~/.local/bin/speedcheck-linux
```

On this computer: Ubuntu 26.04.1 LTS, GNOME 50.1, ARM64, Wayland. Ubuntu's
AppIndicator extension and native Ayatana library were already present. If the
library exists but its introspection binding is missing, the installer downloads
Ubuntu's `gir1.2-ayatanaappindicator3-0.1` package and extracts that binding into
the app's own folder. This fallback requires no administrator access. It does not
change system package records; prefer the system package when available.

Repeat `./install.sh` to update. It retains preferences and results and stops the
old instance; launch again afterward. The app also appears in Ubuntu's application
launcher as **SpeedCheck Linux**. Login startup is enabled on a fresh installation.

## Usage

Click the panel reading to see the latest results, last successful test, next
test time, and status. The menu offers Test Now, pause/resume, 5/10/15/30/60-minute
intervals, both/download/upload display modes, login startup, and Quit. Display
mode changes only the panel label; every test measures both directions.

The `···` suffix marks an active measurement; values update as bytes transfer.
Upload progress is provisional because socket buffering can temporarily inflate
it. Completed upload results wait for the server acknowledgement. `⚠` means the
last attempt failed or results are older than two testing intervals. The menu
explains the failure and retains the last successful time and readings.

Useful commands forward to the existing instance through the session bus:

```sh
~/.local/bin/speedcheck-linux --status
~/.local/bin/speedcheck-linux --test-now
~/.local/bin/speedcheck-linux --pause
~/.local/bin/speedcheck-linux --resume
~/.local/bin/speedcheck-linux --interval 15
~/.local/bin/speedcheck-linux --display both
~/.local/bin/speedcheck-linux --launch-on-login on
~/.local/bin/speedcheck-linux --quit
```

Launching again reuses the same Gio application instance. Quit cancels a running
measurement and exits; it leaves login startup enabled unless you turn it off.

## Scheduling

The first launch tests immediately when a network route is available. The default
cadence is **900 seconds between starts**, including after a manual test. A test
starting at 10:00 schedules the next for 10:15, regardless of when it finishes.
Changing the interval recalculates from the most recent start. Pause prevents
automatic tests; manual tests remain available. Resume runs one test if overdue.

One GTK timer owns scheduling and worker supervision. No cron jobs or wake timers
are installed. Due times persist across restarts. After suspend, session restart,
or an offline period, only one overdue test starts when a route is available; its
start sets the next due time. Missed intervals are never replayed. HTTPS failures
and captive portals count as failed attempts and retain the next scheduled test.
Clock adjustments can move a wall-clock due time; transfer timing uses a monotonic
clock. No overlapping tests are allowed, including manual requests during a test.

## Measurement method, limits, and data use

Inspired by [m-tse/SpeedCheck](https://github.com/m-tse/SpeedCheck). It uses GET
`https://speed.cloudflare.com/__down?bytes=N` and POST
`https://speed.cloudflare.com/__up`, without server discovery. The upstream README
describes 25 MB down / 10 MB up; inspected upstream source instead requested
50 MB down / 10 MB up. This implementation uses the same endpoints with adaptive
payloads and explicit error checking.

Each direction runs a 64 kB warm-up and three sequential samples. Downloads start
at 1 MB, uploads at 256 kB. Later payloads target about 1.5 seconds based on the
preceding sample, capped at 64 MB down and 32 MB up per request. The final reading
is `sum(actual body bytes) × 8 / sum(monotonic sample seconds) / 1,000,000`.
Warm-ups are excluded from throughput but included in reported data use.

Download timing begins before reading the response body, after headers arrive,
and includes every measured body byte. Upload timing includes request transmission
and the successful response acknowledging receipt. Downloads require the exact
requested byte count and uncompressed content; an incomplete direction fails the
whole attempt. Preferences and the last complete pair are saved atomically.

This is a single-connection estimate to a nearby Cloudflare server, not a promise
of ISP capacity. Wi-Fi, VPNs, competing traffic, Cloudflare routing, TLS/socket
buffering, and server response latency affect readings. On very fast links the
payload caps shorten samples, so latency and buffering matter more; multi-gigabit
capacity can be underestimated. A simulated 2 Gbps test checks conversion,
adaptive growth and payload caps, but does not establish this machine's link rate.

Each request has 4-second connect and socket inactivity timeouts, each direction
has a 24-second budget, and the GTK supervisor kills the separate measurement
process after **60 seconds**, including DNS or upload stalls. A failure preserves
the previous successful pair and leaves the scheduler active. Partial/failed
transfers still consume data.

**Data use:** successful tests range from about **3.9 MB to 193.4 MB total**,
depending on measured speed; protocol overhead is additional. At 15-minute
intervals over 24 hours this is roughly **0.37–18.6 GB/day** (96 tests). Faster
connections approach the upper bound. Pause testing or choose a longer interval
on a metered connection. No history or telemetry is uploaded by this app beyond
the test payloads; Cloudflare sees normal connection metadata, including your IP.

## Files and troubleshooting

- Executable: `~/.local/bin/speedcheck-linux`
- Application and any private binding: `$XDG_DATA_HOME/speedcheck-linux`
  (default `~/.local/share/speedcheck-linux`)
- Preferences: `$XDG_CONFIG_HOME/speedcheck-linux/config.json`
- Cached result and due time: `$XDG_STATE_HOME/speedcheck-linux/state.json`
- Current diagnostic status and bounded log: same state folder, `status.json`
  and `app.log` (default `~/.local/state/speedcheck-linux`)
- Login entry: `$XDG_CONFIG_HOME/autostart/speedcheck-linux.desktop`

If nothing appears, check `gnome-extensions info ubuntu-appindicators@ubuntu.com`.
Enable Ubuntu AppIndicators in the Extensions app. A newly installed extension
may require logout/login; do that yourself after saving your work. The existing
extension was already active on the installation machine. This app needs the
graphical user's session bus and display, so launch it as yourself, never root.

If imports fail, run `/usr/bin/python3` and install the packages in
`dependencies.txt`. If tests fail, inspect `--status` and `app.log`, check internet
access and captive portals, then use Test Now. Errors never replace cached good
readings. There is no external speed-test CLI dependency.

## Development and verification

```sh
/usr/bin/python3 -m unittest discover -s tests -v
```

The focused suite covers decimal conversion, a simulated fast link, real byte
accounting, bounded sizes, deadlines/timeouts, partial response rejection,
start cadence, overlap prevention, pause/resume, offline/suspend catch-up, and
failure persistence. Product acceptance steps are in [docs/acceptance.md](docs/acceptance.md).

For live schedule verification, `speedcheck-linux --verification-interval 10`
temporarily selects ten seconds without saving that interval. Restore with
`speedcheck-linux --interval 15`. A stalled worker can be tested by sending
SIGSTOP to `worker_pid` reported by `--status`; the supervisor must kill it within
60 seconds while the menu and other commands stay responsive.

## Uninstall

```sh
cd ~/repos/SpeedCheckLinux
./uninstall.sh          # retain preferences and cached result
./uninstall.sh --purge  # also delete preferences, results and logs
```

These remove the app, launcher, icon, private binding, and login entry. They do
not remove shared system packages or the source repository.

## Attribution and license

[SpeedCheck by m-tse](https://github.com/m-tse/SpeedCheck) provided the behavioral
inspiration. Its README, screenshot, and Swift source were inspected before
implementation; no upstream source, screenshot or icon is distributed here.
No upstream LICENSE file or declared repository license was present when checked
on 2026-10-20, so no permission to reuse those materials is assumed.

Original SpeedCheck Linux code and icon are distributed under the [MIT license](LICENSE).
Ubuntu packages retain their own licenses and copyright notices, including in
the privately extracted package's `usr/share/doc` directory when used.
