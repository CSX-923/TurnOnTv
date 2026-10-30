<p align="center">
  <img src="docs/banner.png" alt="TurnOnTv. Your PC turns on. Your TV follows. Wakes any Android or Google TV on your PC's HDMI input. Windows and Linux." width="800">
</p>

# TurnOnTv

Turn on your Android TV / Google TV and switch it to your PC's HDMI input when the PC starts or wakes
from sleep, the way a PlayStation or a Switch does.

Consoles do this with HDMI-CEC ("One Touch Play"). Almost no PC graphics card supports CEC, so TurnOnTv
does it over your home network instead, with the **Android TV Remote protocol** (the same one the Google
TV phone app uses). There is no ADB and you don't need developer options. You pair the PC once, and the
connection is encrypted.

## Start here

| You are | Do this |
|---|---|
| **Not technical, or don't want to fiddle** | [Let an AI agent set it up](#let-an-ai-agent-set-it-up): it asks you a few questions and does the rest. |
| **Comfortable with a terminal** | [Install it yourself](#install). |
| **Looking for your TV** | [TVS.md](TVS.md): what tested TVs need. |

## Let an AI agent set it up

[PROMPT.md](PROMPT.md) is a set of instructions for an AI coding agent (Claude Code, Codex, Gemini CLI or
similar). The agent checks your TV and finds out how to switch it to the right input. Then it installs
everything, tests it with you, and tells you what it couldn't test. It works on Windows and Linux, and
it can set up a **different** computer than the one it runs on (for example a gaming PC with no AI tools)
over SSH, and walk you through enabling SSH there.

1. Install an AI coding agent on the computer you use, and open a terminal.
2. Get this repository: `git clone https://github.com/CarlosSV923/TurnOnTv`, or download the
   [ZIP](https://github.com/CarlosSV923/TurnOnTv/archive/refs/heads/main.zip) and extract it.
3. Start the agent in that folder and paste the contents of [PROMPT.md](PROMPT.md), with your TV model and
   which PC is plugged into it.
4. Answer its questions. When the TV shows a pairing code, or a password is needed, **you** type it into
   the terminal the agent opens. The agent never needs to see it.

## How it works

1. When the PC starts (Windows: when you sign in) or wakes from sleep, a scheduled task (Windows) or a
   systemd unit (Linux) runs `turnontv.py on`.
2. The script sends a Wake-on-LAN packet and connects to the TV. It keeps trying for up to 90 seconds,
   because right after boot or resume the network needs a moment.
3. If the TV reports that it is off, it sends `WAKEUP`. If the TV ignores that and still reports off, it
   sends `POWER`. It never sends `POWER` to a TV that might be on, because `POWER` toggles.
4. It switches to your PC's port, with the input key (`KEYCODE_TV_INPUT_HDMI_1` by default) or a
   passthrough URI.

Tested on a TCL Google TV (G08 platform, Android 14) on Ethernet: from standby, the TV comes back on
HDMI 1 in a few seconds.

## Requirements

- An Android TV or Google TV on the same network as the PC.
- **Network standby turned on** on the TV, usually under *Settings → System → Power & energy* (the name
  varies by brand). Without it the TV drops off the network when it is off, and nothing can wake it.
- Python 3.9 or newer on the PC.

## Install

Find your TV's IP address under *Settings → Network*. Keep the TV on during installation: it shows a
pairing code that you type into the installer.

### Windows

```powershell
git clone https://github.com/CarlosSV923/TurnOnTv
cd TurnOnTv
powershell -ExecutionPolicy Bypass -File windows\install.ps1 -TvHost 192.168.1.50 -TvInput HDMI_1
```

For TVs that ignore the input keys (TCL, for one), add `-InputUri <uri>`; see
[TVs that ignore the input keys](#tvs-that-ignore-the-input-keys).

This creates a scheduled task, `TurnOnTv`, that runs when you sign in and when Windows wakes from sleep or
hibernation. Test it with `Start-ScheduledTask -TaskName TurnOnTv`. To remove it, run
`windows\uninstall.ps1`; add `-Forget` to also delete the pairing.

### Linux (systemd)

```bash
git clone https://github.com/CarlosSV923/TurnOnTv
cd TurnOnTv
linux/install.sh --host 192.168.1.50 --input HDMI_1
```

Add `--input-uri <uri>` for TVs that ignore the input keys.

This installs `turnontv-boot.service` (at boot, once the network is up) and `turnontv-resume.service`
(after suspend or hibernation). Both run as your user. Test them with
`sudo systemctl start turnontv-boot.service`. To remove them, run `linux/uninstall.sh`; add `--forget` to
also delete the pairing.

## Manual use

```bash
python turnontv.py pair --host 192.168.1.50   # pair once
python turnontv.py on                          # wake + switch to the configured input
python turnontv.py on --input HDMI_2           # another input this time
python turnontv.py input "content://..."       # test a passthrough URI
python turnontv.py off                         # put the TV to sleep
python turnontv.py status                      # on/off, current app, model
```

Use the `python` from the `.venv` folder that the installer creates. Add `-v` to any command for
detailed logs.

## Settings and logs

| | Windows | Linux |
|---|---|---|
| Pairing and settings | `%APPDATA%\TurnOnTv\` | `~/.config/turnontv/` |
| Log | `%APPDATA%\TurnOnTv\turnontv.log` | `~/.config/turnontv/turnontv.log` |

`config.json` holds:

| Key | Meaning |
|---|---|
| `host` | The TV's IP address. Give the TV a fixed address (a DHCP reservation in your router) so it doesn't change. |
| `mac` | The MAC address used for Wake-on-LAN, read during pairing. The TV reports its Wi-Fi MAC; if it is on Ethernet, use a list with both, e.g. `["aa:bb:cc:00:11:22", "dd:ee:ff:33:44:55"]`. Find the wired one with `arp -a <tv ip>` (Windows) or `ip neigh show <tv ip>` (Linux) after reaching the TV. |
| `input` | `HDMI_1` to `HDMI_4`. |
| `input_uri` | Optional. For TVs that ignore the input keys: a passthrough URI such as `content://android.media.tv/passthrough/<input id>`. It is sent as an app link instead of the key. |
| `wol` | `false` turns Wake-on-LAN off. |

## TVs that ignore the input keys

Some firmware ignores `KEYCODE_TV_INPUT_HDMI_*`. For those, TurnOnTv can open the input's passthrough
channel instead: `content://android.media.tv/passthrough/<input id>`, where the `/` characters in the input
id are written as `%2F`.

[TVS.md](TVS.md) lists the URIs that worked on tested TVs, and input ids from the
[cleanyourtv](https://github.com/Gathin23/cleanyourtv) project for other models. For any other TV, run
`adb shell dumpsys tv_input | grep -i hdmi` once with USB debugging on. Test a URI with
`turnontv.py input "<uri>"` before you put it in the config.

## Troubleshooting

- **The TV doesn't wake while it's off, but `on` works while it's on.** Network standby is off, or the TV
  only wakes over Wi-Fi and not over Ethernet (or the other way round). Check the TV's power settings, and
  try the other connection.
- **The TV wakes but stays on the home screen.** See
  [TVs that ignore the input keys](#tvs-that-ignore-the-input-keys).
- **`off` does nothing.** Some firmware (TCL) ignores `SLEEP`. TurnOnTv sends `POWER` when the TV reports
  that it is on, and `SLEEP` only when the TV doesn't report its state.
- **"The TV no longer accepts this computer".** The TV forgot the pairing (for example after a factory
  reset). Run `turnontv.py pair` again.
- **Windows: nothing happens after waking from sleep.** Open Event Viewer → *Windows Logs → System* and
  check that *Power-Troubleshooter* logs event 1 on wake. That event is the trigger the task waits for.

## Credits

Built on [androidtvremote2](https://github.com/tronikos/androidtvremote2). The logo (`docs/logo.svg`,
`docs/logo.png`) is a nod to [CleanYourTV](https://github.com/Gathin23/cleanyourtv)'s TV, and the banner is
set in [Outfit](https://fonts.google.com/specimen/Outfit) (SIL Open Font License). MIT licensed.
