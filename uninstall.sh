#!/bin/bash
set -euo pipefail
data_root=${XDG_DATA_HOME:-"$HOME/.local/share"}
config_root=${XDG_CONFIG_HOME:-"$HOME/.config"}
state_root=${XDG_STATE_HOME:-"$HOME/.local/state"}
binary="$HOME/.local/bin/speedcheck-linux"
if [[ -x "$binary" ]] && [[ -n ${DBUS_SESSION_BUS_ADDRESS:-} ]]; then
    "$binary" --quit >/dev/null 2>&1 || true
fi
rm -f "$binary" "$data_root/applications/speedcheck-linux.desktop" \
    "$data_root/icons/hicolor/scalable/apps/speedcheck-linux.svg" \
    "$config_root/autostart/speedcheck-linux.desktop"
rm -rf "$data_root/speedcheck-linux"
if [[ ${1:-} == --purge ]]; then
    rm -rf "$config_root/speedcheck-linux" "$state_root/speedcheck-linux"
fi
echo 'SpeedCheck Linux uninstalled. Preferences/results retained unless --purge was supplied.'
