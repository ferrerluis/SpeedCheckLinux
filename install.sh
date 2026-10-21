#!/bin/bash
set -euo pipefail
source_dir=$(cd -- "$(dirname -- "$0")" && pwd)
data_root=${XDG_DATA_HOME:-"$HOME/.local/share"}
config_root=${XDG_CONFIG_HOME:-"$HOME/.config"}
destination="$data_root/speedcheck-linux"
binary="$HOME/.local/bin/speedcheck-linux"
/usr/bin/python3 -c 'import gi, requests; gi.require_version("Gtk", "3.0"); from gi.repository import Gtk'
if [[ -x "$binary" ]]; then "$binary" --quit >/dev/null 2>&1 || true; fi
mkdir -p "$destination" "$HOME/.local/bin" "$data_root/applications" "$data_root/icons/hicolor/scalable/apps"
cp -R "$source_dir/speedcheck_linux" "$source_dir/assets" "$destination/"
cp "$source_dir/LICENSE" "$destination/"
extension_uuid="speedcheck-panel@speedcheck-linux"
extension_dir="$data_root/gnome-shell/extensions/$extension_uuid"
extension_fresh=true
if [[ -f "$extension_dir/metadata.json" ]]; then extension_fresh=false; fi
mkdir -p "$extension_dir"
cp "$source_dir/gnome-extension/"*.js "$source_dir/gnome-extension/metadata.json" "$extension_dir/"
if [[ "$extension_fresh" == true && -n ${DBUS_SESSION_BUS_ADDRESS:-} ]]; then
    /usr/bin/python3 - "$extension_uuid" <<'PY'
import sys
from gi.repository import Gio
settings = Gio.Settings.new('org.gnome.shell')
uuid = sys.argv[1]
enabled = settings.get_strv('enabled-extensions')
if uuid not in enabled:
    settings.set_strv('enabled-extensions', enabled + [uuid])
disabled = settings.get_strv('disabled-extensions')
if uuid in disabled:
    settings.set_strv('disabled-extensions', [item for item in disabled if item != uuid])
Gio.Settings.sync()
PY
fi
if ! /usr/bin/python3 -c 'import gi; gi.require_version("AyatanaAppIndicator3", "0.1"); from gi.repository import AyatanaAppIndicator3' 2>/dev/null; then
    # Ubuntu sometimes ships the native library without its small introspection binding.
    # Extract the distribution's binding for this user; no system files are changed.
    if ! /sbin/ldconfig -p | grep 'libayatana-appindicator3.so.1' >/dev/null; then
        echo 'Install dependencies first: sudo apt install python3-gi python3-requests gir1.2-gtk-3.0 gir1.2-ayatanaappindicator3-0.1' >&2
        exit 1
    fi
    mkdir -p "$destination/vendor"
    (
        cd "$destination/vendor"
        apt-get download gir1.2-ayatanaappindicator3-0.1
        for package in gir1.2-ayatanaappindicator3-0.1_*.deb; do
            dpkg-deb -x "$package" .
            rm "$package"
        done
    )
fi
# A tiny Python launcher handles paths with spaces and user-local typelibs safely.
/usr/bin/python3 - "$binary" "$destination" <<'PY'
import pathlib, sys
binary, destination = map(pathlib.Path, sys.argv[1:])
binary.write_text('#!/usr/bin/python3\nimport os, sys\nfrom pathlib import Path\n'
    f'root = {str(destination)!r}\n'
    'vendor = os.pathsep.join(str(p) for p in Path(root + "/vendor").rglob("girepository-1.0"))\n'
    'os.environ["GI_TYPELIB_PATH"] = vendor + os.pathsep + os.environ.get("GI_TYPELIB_PATH", "")\n'
    'sys.path.insert(0, root)\n'
    'from speedcheck_linux.app import main\n'
    'if __name__ == "__main__":\n    raise SystemExit(main())\n')
binary.chmod(0o755)
PY
cp "$source_dir/assets/speedcheck-linux.svg" "$data_root/icons/hicolor/scalable/apps/"
/usr/bin/python3 - "$data_root/applications/speedcheck-linux.desktop" "$binary" "$config_root" <<'PY'
import json, pathlib, sys
desktop, binary, config = map(pathlib.Path, sys.argv[1:])
quoted = str(binary).replace('\\', '\\\\').replace('"', '\\"').replace('`', '\\`').replace('$', '\\$')
text = ('[Desktop Entry]\nType=Application\nName=SpeedCheck Linux\n'
        'Comment=Internet speed in the top panel\n'
        f'Exec="{quoted}"\nTryExec={binary}\nIcon=speedcheck-linux\n'
        'Terminal=false\nCategories=Network;Utility;\nStartupNotify=false\n')
desktop.write_text(text)
prefs = config / 'speedcheck-linux/config.json'
try:
    launch = json.loads(prefs.read_text()).get('launch_on_login', True)
except (OSError, ValueError):
    launch = True
autostart = config / 'autostart/speedcheck-linux.desktop'
if launch:
    autostart.parent.mkdir(parents=True, exist_ok=True)
    autostart.write_text(text + 'X-GNOME-Autostart-enabled=true\n')
else:
    autostart.unlink(missing_ok=True)
PY
if command -v update-desktop-database >/dev/null; then update-desktop-database "$data_root/applications"; fi
echo "Installed: $binary"
echo "Launch: $binary"
echo 'Panel helper installed. A first installation may need login again to load it; existing enabled state is preserved on updates.'
