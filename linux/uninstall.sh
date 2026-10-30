#!/usr/bin/env bash
# Remove the TurnOnTv systemd units. Add --forget to also delete the pairing and settings.
# Usage: linux/uninstall.sh [--forget]
set -euo pipefail

for unit in turnontv-boot.service turnontv-resume.service; do
    if [ -f "/etc/systemd/system/$unit" ]; then
        sudo systemctl disable "$unit" || true
        sudo rm -f "/etc/systemd/system/$unit"
        echo "Removed $unit."
    fi
done
sudo systemctl daemon-reload

if [ "${1:-}" = "--forget" ]; then
    rm -rf "${XDG_CONFIG_HOME:-$HOME/.config}/turnontv"
    echo "Deleted the pairing and settings. The TV may still list this computer as a paired remote."
fi
