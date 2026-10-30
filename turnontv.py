#!/usr/bin/env python3
"""TurnOnTv: wake an Android TV / Google TV and switch it to the PC's HDMI input.

It talks to the TV over the Android TV Remote protocol (the one the Google TV phone app uses), so it
needs no ADB and no developer options. Pair once, then run `turnontv.py on` whenever the PC starts or
wakes up; the install scripts in windows/ and linux/ hook that up for you.

    turnontv.py pair --host 192.168.1.50     pair with the TV (it shows a 6-character code)
    turnontv.py on                           wake the TV and switch to the configured input
    turnontv.py off                          put the TV to sleep
    turnontv.py input HDMI_2                 switch input only
    turnontv.py status                       show whether the TV is on
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import logging.handlers
import os
import socket
import sys
import time
from pathlib import Path

from androidtvremote2 import AndroidTVRemote, CannotConnect, ConnectionClosed, InvalidAuth

CLIENT_NAME = "TurnOnTv"
DEFAULT_INPUT = "HDMI_1"
LOG = logging.getLogger("turnontv")


def default_config_dir() -> Path:
    if os.name == "nt":
        return Path(os.environ.get("APPDATA", Path.home())) / "TurnOnTv"
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "turnontv"


class Config:
    def __init__(self, directory: Path):
        self.dir = directory
        self.file = directory / "config.json"
        self.certfile = str(directory / "cert.pem")
        self.keyfile = str(directory / "key.pem")
        # utf-8-sig: Windows PowerShell 5.1 and Notepad may save the file with a byte-order mark.
        self.data = json.loads(self.file.read_text(encoding="utf-8-sig")) if self.file.exists() else {}

    def save(self) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        self.file.write_text(json.dumps(self.data, indent=2) + "\n", encoding="utf-8")

    def require_host(self) -> str:
        host = self.data.get("host")
        if not host:
            sys.exit(f"Not paired yet: run `turnontv.py pair --host <tv ip>` first ({self.file} is missing).")
        return host


def setup_logging(directory: Path, verbose: bool) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    # The scheduled task and the systemd units run without a console: the log file is how you see what happened.
    to_file = logging.handlers.RotatingFileHandler(directory / "turnontv.log", maxBytes=256_000, backupCount=1,
                                                   encoding="utf-8")
    to_file.setFormatter(fmt)
    handlers = [to_file]
    if sys.stderr is not None:
        to_console = logging.StreamHandler()
        to_console.setFormatter(fmt)
        handlers.append(to_console)
    logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO, handlers=handlers)
    # androidtvremote2 logs every reconnect attempt at INFO; keep it for -v only.
    logging.getLogger("androidtvremote2").setLevel(logging.DEBUG if verbose else logging.WARNING)


def send_wol(mac: str) -> None:
    """Wake-on-LAN magic packet. Harmless when the TV ignores it or is already awake."""
    raw = bytes.fromhex(mac.replace(":", "").replace("-", ""))
    if len(raw) != 6:
        LOG.warning("Skipping Wake-on-LAN: %r is not a MAC address", mac)
        return
    packet = b"\xff" * 6 + raw * 16
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        for port in (9, 7):
            try:
                sock.sendto(packet, ("255.255.255.255", port))
            except OSError as err:   # no network yet, right after boot or resume
                LOG.debug("Wake-on-LAN send failed: %s", err)


def mac_list(value) -> list[str]:
    """`mac` is one address or a list: the TV reports its Wi-Fi MAC, and a TV on Ethernet wakes on the wired one."""
    if not value:
        return []
    return [value] if isinstance(value, str) else list(value)


def make_remote(cfg: Config, host: str) -> AndroidTVRemote:
    return AndroidTVRemote(CLIENT_NAME, cfg.certfile, cfg.keyfile, host, enable_ime=False)


async def connect(cfg: Config, timeout: float, wake: bool) -> AndroidTVRemote:
    """Connect, retrying until the deadline: after boot or resume the PC's network, and the TV's, need a moment."""
    host = cfg.require_host()
    macs = mac_list(cfg.data.get("mac")) if wake and cfg.data.get("wol", True) else []
    deadline = time.monotonic() + timeout
    attempt = 0
    while True:
        attempt += 1
        for mac in macs:
            send_wol(mac)
        remote = make_remote(cfg, host)
        try:
            await remote.async_connect()
            LOG.info("Connected to %s (attempt %d)", host, attempt)
            return remote
        except InvalidAuth:
            sys.exit("The TV no longer accepts this computer: run `turnontv.py pair` again.")
        except (CannotConnect, ConnectionClosed, OSError) as err:
            remote.disconnect()
            if time.monotonic() >= deadline:
                sys.exit(f"Could not reach the TV at {host} within {timeout:.0f} s ({err}). Is it plugged in, with "
                         "network standby on?")
            LOG.debug("Attempt %d failed: %s", attempt, err)
            await asyncio.sleep(3)


async def wait_for_power_state(remote: AndroidTVRemote, timeout: float) -> bool | None:
    """The TV reports whether its screen is on shortly after connecting; None if it never said."""
    deadline = time.monotonic() + timeout
    while remote.is_on is None and time.monotonic() < deadline:
        await asyncio.sleep(0.2)
    return remote.is_on


async def wait_until_on(remote: AndroidTVRemote, timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while not remote.is_on and time.monotonic() < deadline:
        await asyncio.sleep(0.3)
    return bool(remote.is_on)


def input_key(name: str) -> str:
    name = name.upper().removeprefix("KEYCODE_").removeprefix("TV_INPUT_")
    return f"KEYCODE_TV_INPUT_{name}"


def switch_input(remote: AndroidTVRemote, cfg: Config, override: str | None) -> None:
    if override and "://" in override:
        uri = override
    else:
        uri = None if override else cfg.data.get("input_uri")
    if uri:
        # A passthrough channel URI (content://android.media.tv/passthrough/<input id>) for TVs that ignore the key.
        LOG.info("Switching input with %s", uri)
        remote.send_launch_app_command(uri)
        return
    key = input_key(override or cfg.data.get("input", DEFAULT_INPUT))
    LOG.info("Switching input with %s", key)
    remote.send_key_command(key)


async def cmd_pair(cfg: Config, args: argparse.Namespace) -> None:
    remote = make_remote(cfg, args.host)
    cfg.dir.mkdir(parents=True, exist_ok=True)
    if await remote.async_generate_cert_if_missing():
        LOG.info("Created a client certificate in %s", cfg.dir)
    name, mac = await remote.async_get_name_and_mac()
    print(f"Found {name} ({mac}). A pairing code is now shown on the TV.")
    await remote.async_start_pairing()
    while True:
        code = input("Enter the code shown on the TV: ").strip()
        try:
            await remote.async_finish_pairing(code)
            break
        except InvalidAuth:
            print("That code was not accepted, try again.")
        except ConnectionClosed:
            print("The TV closed the pairing screen; starting over.")
            await remote.async_start_pairing()
    # Keep MACs added by hand (the Ethernet one) when pairing again.
    macs = mac_list(cfg.data.get("mac"))
    if mac and mac not in macs:
        macs.insert(0, mac)
    cfg.data.update({"host": args.host, "mac": macs[0] if len(macs) == 1 else macs, "name": name})
    cfg.data.setdefault("input", args.input or DEFAULT_INPUT)
    if args.input:
        cfg.data["input"] = args.input
    if args.input_uri:
        cfg.data["input_uri"] = args.input_uri
    cfg.data.setdefault("wol", True)
    cfg.save()
    print(f"Paired. Settings saved to {cfg.file}")


async def cmd_on(cfg: Config, args: argparse.Namespace) -> None:
    remote = await connect(cfg, args.timeout, wake=True)
    try:
        state = await wait_for_power_state(remote, 5)
        if not state:
            # WAKEUP, not POWER: POWER toggles and would switch off a TV that turned out to be on.
            LOG.info("TV is %s, sending WAKEUP", "off" if state is False else "in an unknown state")
            remote.send_key_command("KEYCODE_WAKEUP")
            if not await wait_until_on(remote, 6) and remote.is_on is False:
                # Some firmware (TCL) ignores WAKEUP. POWER is safe here: the TV itself just said it is off.
                LOG.info("No response to WAKEUP, sending POWER")
                remote.send_key_command("KEYCODE_POWER")
            if not await wait_until_on(remote, 20):
                LOG.warning("The TV did not report being on; switching input anyway")
            await asyncio.sleep(args.settle)   # let the TV finish waking before it is asked to change input
        else:
            LOG.info("TV is already on")
        if not args.no_input:
            switch_input(remote, cfg, args.input)
            await asyncio.sleep(1)   # the key is sent asynchronously; give it time to leave before disconnecting
    finally:
        remote.disconnect()


async def cmd_off(cfg: Config, args: argparse.Namespace) -> None:
    remote = await connect(cfg, args.timeout, wake=False)
    try:
        state = await wait_for_power_state(remote, 5)
        if state is False:
            LOG.info("TV is already off")
            return
        if state is None:
            # Unknown: POWER toggles, so it could switch the TV on. SLEEP never does, but some firmware ignores it.
            remote.send_key_command("KEYCODE_SLEEP")
            LOG.info("Power state unknown, sent SLEEP")
        else:
            # POWER, not SLEEP: TCL ignores SLEEP, and the TV just said it is on, so the toggle turns it off.
            remote.send_key_command("KEYCODE_POWER")
            LOG.info("Sent POWER")
        await asyncio.sleep(1)
    finally:
        remote.disconnect()


async def cmd_input(cfg: Config, args: argparse.Namespace) -> None:
    remote = await connect(cfg, args.timeout, wake=False)
    try:
        switch_input(remote, cfg, args.name)
        await asyncio.sleep(1)
    finally:
        remote.disconnect()


async def cmd_status(cfg: Config, args: argparse.Namespace) -> None:
    remote = await connect(cfg, args.timeout, wake=False)
    try:
        state = await wait_for_power_state(remote, 5)
        info = remote.device_info or {}
        print(f"{cfg.data.get('name', 'TV')} at {cfg.data['host']}: "
              f"{'on' if state else 'off' if state is False else 'unknown'}"
              f"{', app ' + remote.current_app if remote.current_app else ''}"
              f"{', ' + info.get('model', '') if info.get('model') else ''}")
    finally:
        remote.disconnect()


def main() -> None:
    parser = argparse.ArgumentParser(description="Wake an Android TV / Google TV and switch it to an HDMI input.")
    parser.add_argument("--config-dir", type=Path, default=default_config_dir(),
                        help="where the pairing and settings live (default: %(default)s)")
    parser.add_argument("-v", "--verbose", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("pair", help="pair with the TV; it shows a code to type here")
    p.add_argument("--host", required=True, help="the TV's IP address")
    p.add_argument("--input", help=f"input to switch to on `on` (default {DEFAULT_INPUT}): HDMI_1 to HDMI_4")
    p.add_argument("--input-uri", help="passthrough URI for TVs that ignore the input keys (see README)")

    p = sub.add_parser("on", help="wake the TV and switch to the configured input")
    p.add_argument("--input", help="this input instead of the configured one, e.g. HDMI_2")
    p.add_argument("--no-input", action="store_true", help="only wake the TV")
    p.add_argument("--timeout", type=float, default=90, help="seconds to keep trying to reach the TV")
    p.add_argument("--settle", type=float, default=3, help="seconds to wait after waking before switching input")

    p = sub.add_parser("off", help="put the TV to sleep")
    p.add_argument("--timeout", type=float, default=15)

    p = sub.add_parser("input", help="switch input without waking the TV")
    p.add_argument("name", help="HDMI_1 to HDMI_4")
    p.add_argument("--timeout", type=float, default=15)

    p = sub.add_parser("status", help="show whether the TV is on")
    p.add_argument("--timeout", type=float, default=15)

    args = parser.parse_args()
    cfg = Config(args.config_dir)
    setup_logging(cfg.dir, args.verbose)
    handler = {"pair": cmd_pair, "on": cmd_on, "off": cmd_off, "input": cmd_input, "status": cmd_status}[args.command]
    try:
        asyncio.run(handler(cfg, args))
    except SystemExit as err:
        if err.code not in (None, 0):
            LOG.error("%s", err.code)
        raise


if __name__ == "__main__":
    main()
