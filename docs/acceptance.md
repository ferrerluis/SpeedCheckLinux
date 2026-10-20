# Product acceptance catalog v1

Run on Ubuntu with the AppIndicator extension active. Record timestamps, revision,
dependency versions, results, and evidence in an untracked `evidence/` folder.
Each required case below is a single sub-test; all six must pass for acceptance.

| ID | Prerequisites and repeatable steps | Expected outcome and evidence |
|---|---|---|
| TC01.1 Real measurement | Install, launch, wait at most 65 seconds; run `speedcheck-linux --status`. | Both real Cloudflare speeds > 0; transferred byte counts/durations consistent with decimal Mbps; progress changes; completed state retained. Save status and measurement log. |
| TC02.1 Panel/menu | With a completed test, inspect top-right panel and open its menu. Exercise display selections, Test Now, pause/resume, and login toggle. | Numerical download/upload label visible; latest readings and last/next times shown; menu actions work and changes appear in state/autostart. Save screenshot/accessibility and D-Bus menu evidence. |
| TC03.1 Automatic schedule | Set `--verification-interval 10`, observe an automatic start without manual action, then `--interval 15`. | Only one test runs; next start time is start + 10 seconds during verification and start + 900 after restore. Save before/after status. Unit checks cover suspend/offline catch-up without replay. |
| TC04.1 Relaunch/persistence | Pause; select upload-only and interval 30; record status. Launch again, then quit/start, finally restore both/15/resumed. | Relaunch keeps the same process; restart restores preferences, cached result and next due; exactly one registered indicator/application. Save process IDs/status before/after and restored state. |
| TC05.1 Failure recovery | With cached success, launch a test, SIGSTOP its worker, and wait for the 60-second watchdog. Inspect status, then use a short verification interval for the next automatic test and restore 15. | UI responds while stalled; worker is killed by deadline; cached results remain with failure indication; future test is scheduled and succeeds. Save timeout and recovery status. Run focused `unittest` checks. |
| TC06.1 Installation/startup | Check desktop/autostart entries, executable path and permissions; run installer twice with preferences changed. Test installer/uninstaller in isolated XDG directories. | Login entry points at the working user executable, toggle persists across reinstall, Quit stops app, uninstall removes only its own files and optionally purges state. Save command output and final entry. |
