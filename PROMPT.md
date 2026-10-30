# TurnOnTv setup prompt

Paste everything below the line into an AI coding agent (Claude Code, Codex, Gemini CLI or similar),
started in a copy of this repository. Fill in the two lines under "About my setup" first, or leave them
blank and the agent will ask.

---

Set up TurnOnTv from this repository so that my TV turns on and switches to my PC's HDMI input whenever
that PC starts or wakes from sleep, the way a game console does. Talk to me in my language, and explain
each step in plain words: I may not be technical.

About my setup:
- TV brand and model (if I know it):
- The PC that is plugged into the TV, and which HDMI port it uses:

## Rules

- **Use this repository's tools.** Use `turnontv.py`, `windows/install.ps1` and `linux/install.sh`. Don't
  write a new script, and don't change these ones unless one of them fails. If you fix a bug in one, tell
  me what you changed.
- **I type the secrets.** Never type the TV's pairing code, a password or a `sudo` password yourself, and
  never ask me to paste them into the chat. Run the step that needs one in a terminal I can type into, and
  wait for me.
- **Ask before you install software or accept a license.** That includes Python, packages from a store,
  and the SSH server. Tell me what it is and where it comes from.
- **The installer creates a scheduled task (Windows) or systemd units (Linux).** Your tool may ask me to
  approve that, because it stays on the PC. Explain this before you run it.
- **Check the result after every step.** Some steps only show on the TV. Then ask me what I see ("did the
  TV switch to HDMI 1?") instead of assuming it worked.
- **Leave nothing open that wasn't there before.** If you switch on ADB or an SSH server for the setup,
  offer to switch it off at the end, and do it if I agree.

## Step 1: which computer, which systems

Ask me:

1. **Where should TurnOnTv be installed?** On the computer you are running on, or on another one: the PC
   that is plugged into the TV, often a gaming PC with no AI tools on it.
2. **Which operating system does each computer run?** For the target, Windows or Linux. For the computer
   you are running on, Windows, macOS or Linux. Check the one you are running on yourself.

TurnOnTv can install its triggers on Windows and Linux. macOS can run `turnontv.py` by hand, but there is
no installer for it. If the target is a Mac, tell me so, and stop.

If the target is this computer, skip to step 3. Otherwise, do step 2 first.

## Step 2: reach the other PC over SSH (only when the target is another computer)

Every later step then runs on the target over SSH. Steps that need me to type something (the pairing
code, a `sudo` password) run with `ssh -t` in a terminal I can type into.

### 2a. Turn on the SSH server on the target

I do this on the target PC. Give me the exact commands.

- **Target is Windows 10/11.** In PowerShell **as administrator**:
  ```powershell
  Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0
  Start-Service sshd; Set-Service sshd -StartupType Automatic
  ```
  The first command can take several minutes with no output. That is normal.
- **Target is Linux.** Install and start the OpenSSH server:
  - Debian, Ubuntu or Mint: `sudo apt install openssh-server`, then `sudo systemctl enable --now ssh`.
  - Fedora: `sudo dnf install openssh-server`, then `sudo systemctl enable --now sshd`.
  - Arch: `sudo pacman -S openssh`, then `sudo systemctl enable --now sshd`.

Then find the target: ask me for its IP address, or scan the local network for TCP port 22 and confirm
the address with me. Ask me for my user name on the target.

### 2b. A key so you can run commands without my password

1. **Create a dedicated key** on the computer you run on: `~/.ssh/turnontv_setup`, with no passphrase.
   Don't overwrite or reuse `~/.ssh/id_*`: those may be my own keys. On Windows, create the `.ssh` folder
   first; `ssh-keygen` does not create it, and fails with "No such file or directory".
2. **Authorize it on the target:**
   - **Target is Windows.** Give me this command for an administrator PowerShell on the target, with the
     public key filled in. It works whether or not my account is an administrator; an administrator's keys
     must go in `administrators_authorized_keys`, with these permissions, or sshd ignores them:
     ```powershell
     $k='<public key>'; if (Get-LocalGroupMember -SID S-1-5-32-544 | Where-Object { $_.Name -like "*\$env:USERNAME" }) { $f="$env:ProgramData\ssh\administrators_authorized_keys"; Add-Content -Path $f -Value $k; icacls.exe $f /inheritance:r /grant '*S-1-5-32-544:F' /grant '*S-1-5-18:F' | Out-Null } else { New-Item -ItemType Directory -Force "$env:USERPROFILE\.ssh" | Out-Null; Add-Content -Path "$env:USERPROFILE\.ssh\authorized_keys" -Value $k }; "Key authorized for $env:USERNAME"
     ```
   - **Target is Linux, and you run on macOS or Linux.** Run
     `ssh-copy-id -i ~/.ssh/turnontv_setup.pub <user>@<target>` in a terminal where I type my password.
   - **Target is Linux, and you run on Windows.** There is no `ssh-copy-id` on Windows. Run this in a
     terminal where I type my password:
     `type $env:USERPROFILE\.ssh\turnontv_setup.pub | ssh <user>@<target> "mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"`
3. **Check** with `ssh -i <key> -o BatchMode=yes <user>@<target>` and a harmless command.

### 2c. Running commands on a Windows target

The default SSH shell on Windows is `cmd.exe`, and its quoting breaks PowerShell commands. Send each
PowerShell script as `powershell -NoProfile -NonInteractive -EncodedCommand <base64>`, where the base64 is
the script encoded as UTF-16LE. Lines starting `#< CLIXML` and progress XML in the output are PowerShell
noise; ignore them.

## Step 3: requirements on the target

- **Python 3.9 or newer.**
  - On Windows, a `python.exe` under `WindowsApps` is only the Microsoft Store shortcut, not Python. If
    Python is missing, ask me, then install it for my user only:
    `winget install -e --id Python.Python.3.13 --scope user --accept-package-agreements --accept-source-agreements`.
    This accepts the Python license and winget's terms, so ask me first.
  - On Linux, install `python3` and `python3-venv` (Debian/Ubuntu) with the package manager.
- **This repository on the target.** Use `git clone https://github.com/CarlosSV923/TurnOnTv`. Without git,
  download https://github.com/CarlosSV923/TurnOnTv/archive/refs/heads/main.zip and extract it. A good place
  is the user's home folder (`~/TurnOnTv`, `C:\Users\<user>\TurnOnTv`).
- **Find the TV.** Ask me for its IP address (*Settings → Network* on the TV), or scan the local network
  for TCP ports 6466 and 6467, which every Android TV / Google TV with Google's remote service opens. If
  nothing on the network answers on them, the TV is not an Android TV or Google TV, and TurnOnTv can't drive
  it: tell me, and suggest the HDMI-CEC alternative at the end of this prompt.
- Suggest that I give the TV a fixed IP address in my router (a DHCP reservation), so the setup keeps
  working.

## Step 4: network standby on the TV

Ask me to turn on the setting that keeps the TV on the network while it is off. Without it, nothing can
wake the TV. It usually sits under *Settings → System → Power* (or *Power & energy*), and the name varies:
"Network standby", "Wake on LAN", "Wake on Wireless LAN", "Remote start" (Sony), "Switch on with Wi-Fi"
(Philips). Look up my model in [TVS.md](TVS.md) first.

## Step 5: pair

Before you start, ask me to press **Home** on the remote. A TV left on an HDMI input with no signal may
switch itself off after a few minutes, and the pairing code goes with it. If that happens, stop the
command and run it again; the TV shows a new code.

Run `turnontv.py pair --host <tv ip>` on the target with the virtual environment's Python
(`.venv\Scripts\python.exe` on Windows, `.venv/bin/python` on Linux), in a terminal I can type into. The TV shows a 6-character code. I type it there and it prints
`Paired`.

To get the virtual environment before the installer, run `python -m venv .venv` and
`.venv/bin/pip install -r requirements.txt` (`.venv\Scripts\pip` on Windows) in the repository. Or run the
installer from step 7 right away: it pairs as part of the install.

## Step 6: find what switches the TV to the PC's input

1. Ask me which HDMI port the PC uses.
2. Run `turnontv.py input HDMI_<n>` while the TV shows the home screen, and ask me whether it switched.
3. If it didn't, the firmware ignores the input keys. Find a passthrough URI:
   - Look for my TV (brand, model, platform) in [TVS.md](TVS.md).
   - Look in the [cleanyourtv examples](https://github.com/Gathin23/cleanyourtv/tree/main/examples) (MIT
     licensed). Some lists name the TV's input services, for example
     `com.tcl.tvinput/.TvPassThroughService/HW15` or `com.mediatek.tis/.HdmiInputService/HW2`. Search them
     for my brand and platform and for `Service/HW`.
   - As a last resort, read the input ids from the TV itself with ADB, which needs USB debugging for this
     one command: `adb shell dumpsys tv_input | grep -i -E "hdmi|passthrough"`. Ask me before you switch on
     debugging, and help me switch it off again afterwards.
   - Build the URI as `content://android.media.tv/passthrough/<input id>`, with every `/` in the input id
     written as `%2F`. Test it with `turnontv.py input "<uri>"` and ask me whether the TV switched. Try the
     candidates one at a time.

## Step 7: install the trigger

- **Windows:**
  `powershell -ExecutionPolicy Bypass -File windows\install.ps1 -TvHost <tv ip> -TvInput HDMI_<n> [-InputUri "<uri>"]`
- **Linux:** `linux/install.sh --host <tv ip> --input HDMI_<n> [--input-uri "<uri>"]`. It asks for
  `sudo`; run it with `ssh -t` in a terminal where I can type the password.

If the target is already paired (`config.json` exists), the installer skips pairing. Then add a missing
`input_uri` to the config by hand. Write the file as UTF-8 without a byte-order mark (Windows PowerShell 5.1's
`Set-Content` adds one); turnontv.py reads it either way, but other tools may not.

## Step 8: Wake-on-LAN over Ethernet

During pairing the TV reports its **Wi-Fi** MAC address. If the TV is connected by cable, Wake-on-LAN needs
the **Ethernet** MAC as well. Read the TV's MAC from the target's ARP table after reaching the TV
(Windows: `arp -a <tv ip>`; Linux: `ip neigh show <tv ip>`). If it differs from the one in `config.json`,
make `mac` a list with both: `"mac": ["<wifi mac>", "<ethernet mac>"]`.

The settings are in `%APPDATA%\TurnOnTv\config.json` (Windows) or `~/.config/turnontv/config.json`
(Linux).

## Step 9: test it for real

1. Run `turnontv.py off`, then `turnontv.py status`. It should say `off`. If the TV ignored it, tell me to
   switch it off with the remote.
2. Wait 30 seconds.
3. Run the real trigger, not the script:
   - Windows: `Start-ScheduledTask -TaskName TurnOnTv`, then check `Get-ScheduledTaskInfo -TaskName TurnOnTv`
     (`LastTaskResult` 0).
   - Linux: `sudo systemctl start turnontv-boot.service`.
4. Ask me whether the TV came on, on the PC's input, with the PC's picture. The log
   (`turnontv.log`, next to `config.json`) says what happened. "TV is already on" right after `off` is
   normal: the Wake-on-LAN packet woke it before the script connected.

Tell me what is still untested. On Windows the task runs at **sign-in**, not at power-on, so a PC that asks
for a password wakes the TV once I sign in. Suspend and resume have their own trigger, and only a real
suspend tests them.

## Step 10: finish

- Summarize what is installed and where, and how to remove it (`windows\uninstall.ps1` or
  `linux/uninstall.sh`, with `-Forget`/`--forget` to delete the pairing).
- If you switched on SSH, a key or ADB only for this setup, offer to remove them. For SSH on Windows, that
  means removing the key line from `authorized_keys` or `administrators_authorized_keys`, and
  `Stop-Service sshd; Set-Service sshd -StartupType Disabled`.
- If my TV is not in [TVS.md](TVS.md), offer me a short entry for it: brand, model, platform, Android
  version, the URI or key that worked, and its quirks. Leave out IP addresses, MAC addresses and serial
  numbers.

## When it can't work

If the TV never wakes from standby, try three things before you give up:
- Network standby is on.
- If the TV has both, try the other connection, Wi-Fi or Ethernet.
- The Ethernet MAC is in `mac`.

If it still doesn't wake, say so plainly and suggest the hardware route: a **USB-CEC adapter** (Pulse-Eight)
between the PC and the TV. It makes the PC behave like a console over HDMI-CEC. The TV's HDMI-CEC setting,
and the option that lets a device turn the TV on, must both be enabled.
