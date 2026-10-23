# Standalone GNOME startup fix — 2026-10-23

Tested revision: `40fc881be4a9ce8f6363bfa97830b1178986210e`.
Environment: Ubuntu 26.04.1 LTS, GNOME 50.1, ARM64, Wayland, systemd user manager.

## Cause and fix

After reboot, Launch on login was enabled and the XDG entry existed, but the app
had no process or application bus owner. This computer starts GNOME directly via
`gnome-shell-headless.service`; its graphical-session and XDG autostart targets
were inactive. The normal login entry was generated correctly but never launched.
The original acceptance check verified that entry, without exercising this boot path.

The installer now detects that user-local desktop service and adds only
`speedcheck-linux-headless.service` to its startup dependencies. The app starts
with Wayland, retries failures every five seconds until the display is ready,
and stops with the desktop. The existing login entry gates startup, so the same
Launch on login toggle works. Normal Quit does not restart the app.

The existing desktop service and its process were unchanged. No global autostart
target was activated, and no system package or administrator change was needed.
Uninstall removes only the app's service and startup link.

## Verification

Catalog v4 adds TC08 with three regression sub-tests (catalog total: eight cases,
eleven sub-tests). **TC08.1–TC08.3 passed.** The 14 unchanged core/measurement
checks passed, and both new installer checks passed after the iterations below:
**16 valid automated checks, none skipped**.

| Check | Observed result |
|---|---|
| TC08.1 Startup and late display | Real enabled boot dependency confirmed. An intentionally unavailable Wayland display caused startup failure; removing the test override allowed systemd to recover automatically. One overdue Cloudflare test completed, retaining preferences. |
| TC08.2 Login toggle | Off removed the login file and the service skipped startup with no app owner. Manual launch still worked; on restored service startup and cached readings. |
| TC08.3 Quit, singleton, cleanup | Quit stayed closed for six seconds, longer than the retry delay. Relaunch reused the same PID. Actual isolated normal/headless installations, repeat updates, uninstall and purge preserved unrelated files and respected saved startup settings. |
| Native panel | Current GNOME accessibility tree showed one numerical label at x=1110, y=0, width=110, height=29; one active SpeedCheck indicator was registered. |

The service was left active and enabled, showing **46 Mbps down / 91 Mbps up**,
with both readings, automatic tests every 900 seconds and login startup enabled.
Next due at verification: **2026-10-23 10:07:45 EDT**.

**No reboot or logout was performed.** Verification replayed the real startup
unit in this session, including a late display. A future reboot provides separate
confirmation; these results are not presented as a completed reboot test.

## Iterations and evidence

- An isolated test initially lacked its runtime directory; the fixture was fixed.
- Special-character paths exposed literal quotes in the path condition and excess
  dollar escaping in the executable path. Both were fixed and affected checks rerun.
- The old panel harness assumed a prior-boot accessibility connection and cache
  method. Discovering the current owner and traversing the native tree fixed it.

The ignored `evidence/` folder retains original failed attempts, passing installer
output, live startup/toggle/quit records, panel bounds, installed source hashes,
and machine-readable `startup-results.json`. Earlier unchanged component results
remain historical; this report covers the startup regression and refreshed checks.
