# Installation verification — 2026-10-20

Tested application revision: `2248b48c1905d737f754209e0e6c9600db3cc848`.
The installed Python source and icon matched that revision byte for byte.

Environment: Ubuntu 26.04.1 LTS, GNOME 50.1, Wayland, ARM64, Python 3.14.4,
GTK 3.24.52, PyGObject 3.56.2, Requests 2.32.5, Ayatana 0.5.94.
Ubuntu AppIndicators was already active; no logout or system package changes were required.

The missing Ubuntu introspection package was extracted into the user installation;
the existing system Ayatana library is shared normally.

## Results

**14/14 focused unit tests and 6/6 acceptance cases passed.**

| Case | Outcome | Evidence |
|---|---|---|
| TC01.1 Real measurement | Passed | Multiple real Cloudflare tests completed. Latest: 4.2623 Mbps down / 52.6625 Mbps up at 06:26:16 UTC; exact bytes/durations independently recomputed. A separate curl download supported the earlier download estimate. |
| TC02.1 Panel/menu | Passed | Native screenshots confirmed the numerical panel label, original gauge icon, opened menu, results, last/next times, login checkmark, and all five interval choices with 15 minutes selected. Display modes, interval changes, pause/resume, login toggle, Test Now, overlap prevention and Quit also passed through the menu interface. |
| TC03.1 Scheduling | Passed | A temporary 10-second interval produced an automatic test; restoring 15 minutes produced `next_due = last_start + 900`. A normal scheduled test also started 900.08 seconds after its predecessor. |
| TC04.1 Relaunch/persistence | Passed | Relaunch reused the same process. Full restart retained preferences, cached results and due time; both/15/resumed were restored. |
| TC05.1 Timeout/recovery | Passed | SIGSTOP stalled only the measurement worker. The main app accepted commands, killed the worker at 60 seconds, retained good results, then completed the next automatic test. |
| TC06.1 Installation/startup | Passed | Two installations respected login-off in isolated XDG folders. Purge removed only app files and retained an unrelated sentinel; the normal installation was restored with a working executable and enabled autostart entry. |

The app was left running with both readings, automatic testing enabled every
900 seconds, and launch-on-login enabled. Its next due time at handoff was
**2026-10-20 06:40:57 UTC**; subsequent tests continue from their own start times.

## Native visual verification

GNOME initially denied the screenshot utility, and automatic approval review
rejected monitor capture because it could include sensitive desktop contents.
The user then explicitly authorized any desktop captures needed.

GNOME reported no attached monitor, so a temporary 1280×800 native virtual display
was created in the existing Wayland session. Screenshots showed the actual panel,
opened application menu, and expanded interval submenu; no application mockup was used.

The temporary display was removed after verification. Only still images were
saved locally; a crop containing the SpeedCheck menu and panel is in the ignored
`evidence/panel-menu.png`, and desktop captures were not uploaded to GitHub.

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
