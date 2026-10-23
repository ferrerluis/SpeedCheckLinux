# Sustained download sampling — 2026-10-23

Final application revision: `162ea81f31c284d6d8f16de8253b9544c73ff336`.
Ubuntu 26.04.1 LTS / GNOME 50.1 / Wayland / ARM64; Python 3.14.4,
GTK 3.24.52, PyGObject 3.56.2, Requests 2.32.5.

## Change and scope

The original adaptive download could remain small after a slow initial probe.
Earlier real transfers using the same code measured 24, 38 and 118 Mbps at 1, 8
and 32 MB. The new bounded ramp-up uses larger samples when affordable and takes
the final completed sample once its duration is sufficient or a limit is reached.
It records the exact selected bytes/time separately from total payload consumption.
Slow links can stop early; request timeouts, 24-second direction budgets and the
60-second supervisor remain. Maximum payload use is now about 169.4 MB per test.

## Results

**19/19 automated checks passed, none skipped.** Four focused product checks
passed: TC02.2 and TC09.1–TC09.3. Catalog v6 totals nine cases / fifteen sub-tests;
v5 added sustained sampling, and v6 added CLI display regression coverage.

| Check | Observation |
|---|---|
| TC09.1 Sustained sampling | Simulations reached a large sample despite slow short probes, retained the final sample when earlier speed was higher, respected data limits, and allowed a 0.5 Mbps link to stop after a small sample. |
| TC09.2 Live comparison | App download results were 40.30 and 42.15 Mbps; adjacent independent 64 MB downloads measured 37.77 and 54.07 Mbps. Both paired differences were within 25%. This verifies comparable current throughput, not a 200 Mbps Wi-Fi guarantee. |
| TC09.3 Failure/recovery | A stopped worker timed out at 60 seconds. A display command responded in 0.53 seconds while stopped; cached results survived with a failure marker, and a later automatic test succeeded. Normal 900-second cadence and both-speed display were restored. |
| TC02.2 CLI mode | Modern --display-mode and legacy --display changed live preferences/labels while preserving a single PID, including during the stalled-worker test. |

The final installed application matches the repository. It is left running with
login startup enabled and automatic tests every 15 minutes. Next due at final
verification: **10:55:52 EDT**. Readings and due times subsequently change.

## Iterations

Failure verification exposed an existing GTK option conflict: PyGObject consumes
--display and rewrites argv during import. Normalizing it just before
Application.run was too late. The final fix normalizes before GTK import and
provides --display-mode; both spellings were then verified on the running app.
Earlier failed attempts are retained in local evidence.

A verification command also raced Type=exec startup and temporarily became the
resident singleton. The harness now waits for the service PID to own the app bus
name before commands. The final process is service-managed; startup unit source
was unchanged. Only directly affected checks were rerun.

## Wi-Fi power-saving comparison

**Blocked by host authorization; no off-condition measurements were taken.**
Syn reported “approval unavailable; non-interactive sudo denied.” The Linux
1Password CLI had no authorized account session. The privileged request exited,
and power saving remained on. No Wi-Fi disconnect, persistent network change,
security-policy change or Ethernet/LAN test was performed.

The comparison can proceed through the normal Syn approval flow when the paired
approval device is available. No performance benefit is claimed without that test.

Generated status, benchmark, failure, CLI, source-hash and native panel evidence
remain local in ignored evidence/, including sustained-results.json. Earlier
unchanged component results remain historical; no full reboot test was performed.
