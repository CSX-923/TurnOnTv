#!/usr/bin/env bash
# TurnOnTv for Linux: set up Python, pair with the TV once, and install two systemd units that wake the TV and
# switch it to this PC's input when the PC boots and when it resumes from suspend or hibernation.
#
# Usage (from the repository folder, as your normal user; it asks for sudo to install the units):
#   linux/install.sh --host 192.168.1.50 [--input HDMI_1] [--input-uri <uri>]
# Run it again at any time: it keeps the pairing and only rewrites the units.
set -euo pipefail

TV_HOST=""
TV_INPUT="HDMI_1"
TV_INPUT_URI=""
while [ $# -gt 0 ]; do
    case "$1" in
        --host) TV_HOST="$2"; shift 2 ;;
        --input) TV_INPUT="$2"; shift 2 ;;
        --input-uri) TV_INPUT_URI="$2"; shift 2 ;;
        -h|--help) sed -n '2,8p' "$0"; exit 0 ;;
        *) echo "unknown option: $1" >&2; exit 2 ;;
    esac
done

if [ "$(id -u)" -eq 0 ]; then
    echo "Run this as your normal user, not root: the pairing belongs to your account." >&2
    exit 1
fi

REPO="$(cd "$(dirname "$0")/.." && pwd)"
SCRIPT="$REPO/turnontv.py"
VENV="$REPO/.venv"
CONFIG="${XDG_CONFIG_HOME:-$HOME/.config}/turnontv/config.json"
RUN_USER="$(id -un)"

# 1. A private Python environment next to the script.
if [ ! -x "$VENV/bin/python" ]; then
    command -v python3 >/dev/null || { echo "Python 3.9 or newer is required (python3)." >&2; exit 1; }
    python3 -m venv "$VENV" || { echo "Could not create the environment: install python3-venv and try again." >&2; exit 1; }
fi
"$VENV/bin/python" -m pip install --disable-pip-version-check -q -r "$REPO/requirements.txt"

# 2. Pair once. The TV shows a code; type it here.
if [ ! -f "$CONFIG" ]; then
    [ -n "$TV_HOST" ] || { echo "Not paired yet: run again with --host <tv ip>." >&2; exit 1; }
    "$VENV/bin/python" "$SCRIPT" pair --host "$TV_HOST" --input "$TV_INPUT" ${TV_INPUT_URI:+--input-uri "$TV_INPUT_URI"}
else
    echo "Already paired ($CONFIG). Delete that folder to pair again."
fi

# 3. Two system units that run as you: one at boot (once the network is up), one after every resume.
#    The config path is passed explicitly so it does not depend on the unit's environment.
CONFIG_DIR="$(dirname "$CONFIG")"
EXEC="\"$VENV/bin/python\" \"$SCRIPT\" --config-dir \"$CONFIG_DIR\" on"

sudo tee /etc/systemd/system/turnontv-boot.service >/dev/null <<EOF
[Unit]
Description=TurnOnTv: wake the TV and switch it to this PC at boot
Wants=network-online.target
After=network-online.target

[Service]
Type=oneshot
User=$RUN_USER
ExecStart=$EXEC
TimeoutStartSec=150

[Install]
WantedBy=multi-user.target
EOF

sudo tee /etc/systemd/system/turnontv-resume.service >/dev/null <<EOF
[Unit]
Description=TurnOnTv: wake the TV and switch it to this PC after suspend or hibernation
After=suspend.target hibernate.target hybrid-sleep.target suspend-then-hibernate.target

[Service]
Type=oneshot
User=$RUN_USER
ExecStart=$EXEC
TimeoutStartSec=150

[Install]
WantedBy=suspend.target hibernate.target hybrid-sleep.target suspend-then-hibernate.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable turnontv-boot.service turnontv-resume.service

echo "Installed. Try it now with: sudo systemctl start turnontv-boot.service"
echo "Log: $CONFIG_DIR/turnontv.log   (or: journalctl -u turnontv-boot -u turnontv-resume)"
