# Installation verification — 2026-10-20

Tested application revision: `2248b48c1905d737f754209e0e6c9600db3cc848`.
The installed Python source and icon matched that revision byte for byte.

Environment: Ubuntu 26.04.1 LTS, GNOME 50.1, Wayland, ARM64, Python 3.14.4,
GTK 3.24.52, PyGObject 3.56.2, Requests 2.32.5, Ayatana 0.5.94.
Ubuntu AppIndicators was already active; no logout or system package changes were required.

The missing Ubuntu introspection package was extracted into the user installation;
the existing system Ayatana library is shared normally.

## Results

**14/14 focused unit tests passed. 5/6 acceptance cases passed; one visual check remains blocked.**

| Case | Outcome | Evidence |
|---|---|---|
| TC01.1 Real measurement | Passed | Multiple real Cloudflare tests completed. Latest: 4.1518 Mbps down / 31.0850 Mbps up at 06:11:18 UTC; exact bytes/durations independently recomputed. A separate curl download supported the earlier download estimate. |
| TC02.1 Panel/menu | Blocked for visual opening | GNOME accessibility confirmed the numerical panel label as visible and showing at the top-right. The exported native menu contained the results, last/next times, and all controls. Display modes, interval changes, pause/resume, login toggle, Test Now, overlap prevention and Quit passed through the menu interface. A directly opened menu could not be visually confirmed. |
| TC03.1 Scheduling | Passed | A temporary 10-second interval produced an automatic test; restoring 15 minutes produced `next_due = last_start + 900`. |
| TC04.1 Relaunch/persistence | Passed | Relaunch reused the same process. Full restart retained preferences, cached results and due time; both/15/resumed were restored. |
| TC05.1 Timeout/recovery | Passed | SIGSTOP stalled only the measurement worker. The main app accepted commands, killed the worker at 60 seconds, retained good results, then completed the next automatic test. |
| TC06.1 Installation/startup | Passed | Two installations respected login-off in isolated XDG folders. Purge removed only app files and retained an unrelated sentinel; the normal installation was restored with a working executable and enabled autostart entry. |

The app was left running with both readings, automatic testing enabled every
900 seconds, and launch-on-login enabled. Its next due time at handoff was
**2026-10-20 06:25:57 UTC**; subsequent tests continue from their own start times.

## Visual verification limit

GNOME denied the screenshot utility, and automatic approval review rejected a
monitor-capture session because it could include sensitive desktop contents.
No desktop recording was made; input-only attempts did not establish that the
opened menu was visible, so that part of TC02.1 is not reported as passed.

## Test iteration

The first Quit check waited only 0.5 seconds and observed the process before
asynchronous shutdown finished. The corrected bounded wait measured successful
exit in 1.38 seconds, then restarted the app with its cached results intact.

No application change was needed; only that Quit check was rerun. The
documentation-only follow-up commit does not invalidate the runtime evidence.

## Local evidence

The ignored `evidence/` folder contains the machine-readable acceptance report,
component versions, unit-test output, menu layout/action records, visible panel
accessibility evidence, and before/after state for scheduling, restart and failure.
Generated desktop/session evidence is intentionally excluded from GitHub.
