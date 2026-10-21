#!/bin/bash
set -euo pipefail
data_root=${XDG_DATA_HOME:-"$HOME/.local/share"}
config_root=${XDG_CONFIG_HOME:-"$HOME/.config"}
state_root=${XDG_STATE_HOME:-"$HOME/.local/state"}
binary="$HOME/.local/bin/speedcheck-linux"
extension_uuid="speedcheck-panel@speedcheck-linux"
if [[ -n ${DBUS_SESSION_BUS_ADDRESS:-} ]]; then
    gnome-extensions disable "$extension_uuid" >/dev/null 2>&1 || true
    /usr/bin/python3 - "$extension_uuid" <<'PY'
import sys
from gi.repository import Gio
settings = Gio.Settings.new('org.gnome.shell')
for key in ('enabled-extensions', 'disabled-extensions'):
    settings.set_strv(key, [item for item in settings.get_strv(key) if item != sys.argv[1]])
Gio.Settings.sync()
PY
fi
if [[ -x "$binary" ]] && [[ -n ${DBUS_SESSION_BUS_ADDRESS:-} ]]; then
    "$binary" --quit >/dev/null 2>&1 || true
fi
rm -f "$binary" "$data_root/applications/speedcheck-linux.desktop" \
    "$data_root/icons/hicolor/scalable/apps/speedcheck-linux.svg" \
    "$config_root/autostart/speedcheck-linux.desktop"
rm -rf "$data_root/speedcheck-linux"
rm -rf "$data_root/gnome-shell/extensions/$extension_uuid"
if [[ ${1:-} == --purge ]]; then
    rm -rf "$config_root/speedcheck-linux" "$state_root/speedcheck-linux"
fi
echo 'SpeedCheck Linux uninstalled. Preferences/results retained unless --purge was supplied.'
