# Narrow panel verification — 2026-10-21

Tested code revision: `dfb95cce57c3286d8589cb4748655f2834c1f353`.
Ubuntu 26.04.1 LTS, GNOME 50.1, Wayland, ARM64; Python 3.14.4,
GTK 3.24.52, PyGObject 3.56.2, Requests 2.32.5, Ayatana 0.5.94.
Installed application and canonical helper files matched the repository byte for byte.

The native clock now sits beside Activities. SpeedCheck displays only download
and upload text; the right panel uses the remaining width instead of half the
screen. The launcher keeps its separate application icon.

## Results

Catalog v3 contains **7 cases / 8 sub-tests**. All are passed, with earlier evidence
carried forward only for unchanged behavior. **14 focused unit tests passed.**

| Checks | Evidence and outcome |
|---|---|
| TC07.1 Native layout and menus | Actual GNOME 640×800 and 800×800 screenshots show both speeds without the gauge or clock overlap. SpeedCheck's native menu and the clock calendar opened correctly. Disabling restored the centered clock; re-enabling restored the left clock. |
| TC07.2 Resize | With the helper continuously enabled, 640→800→640 retained complete speed text without ellipses. Independent accessible rectangles put every existing panel control in bounds. At the final 640 width, clock x=67..202, SpeedCheck x=227..345. |
| TC06.1 Install and undo | A real repeat install retained the helper's disabled preference. Actual uninstall removed the helper/app and restored the centered clock. Reinstall/restart restored the layout, cached results, both-speed display, 15-minute interval and launch-on-login. The autostart entry points to the working user executable. |
| TC02.1 Panel/menu | Native panel and opened menu rechecked after changes, including cached failure and subsequent successful readings. Earlier menu-control activation evidence remains valid: definitions and callbacks are unchanged. |
| TC01.1, TC03.1, TC04.1, TC05.1 | Earlier measurement, cadence, single-instance/persistence and timeout/recovery evidence remains valid because those components are unchanged. Current reinstall retained state; a normal automatic test completed after the update and cleared the failure marker. |

The latest successful automatic test recorded 1.7782 Mbps down / 1.4149 Mbps up at
01:26:26 UTC. These are observations of this connection, not its maximum capacity.
A subsequent attempt timed out and retained that pair; the next test remained
scheduled for 01:56:02 UTC. Tests continue every 900 seconds, so readings and due
times change afterward.

The helper was activated live through GNOME's native extension machinery; no
logout was needed. GNOME reported no monitor before verification. Temporary
native test displays were removed afterward; the app and helper remain active.

## Fixed iterations

- Centered clock overlap reproduced. Moving the clock alone still clipped speed
  text because GNOME capped the right box at half the panel width.
- An initial width constraint pushed other controls beyond the viewport. Native
  allocation of the remaining width fixed that; TC07.2 now guards resizing and
  every control's bounds. Previous affected layout passes were rerun.
- The first restore path used a nonexistent Clutter method. Restoring the visible
  property fixed it; disable/enable and full uninstall/reinstall passed afterward.
- Verification infrastructure needed symlink-preserving package backups, capture
  keepalive, and a stable label selector. Affected checks were rerun; failed harness
  attempts did not count as product passes.

Generated evidence remains local in the ignored `evidence/` directory, including
cropped panel/menu images, geometry, install output, source hashes, unit output,
and `panel-layout-results.json`. Full desktop captures are not published.
The [original verification](verification.md) retains the initial-build history.
