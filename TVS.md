# TVs

What each TV needs to wake up and switch to the PC with TurnOnTv. Look for your TV here before you
experiment, and add a row once yours works ([PROMPT.md](PROMPT.md), step 10). Leave out IP addresses, MAC
addresses and serial numbers.

## Tested with TurnOnTv

| TV | Platform / Android | Network standby setting | Wakes over | Input switch | Quirks |
|---|---|---|---|---|---|
| TCL Google TV ("Smart TV Pro"), Latin America firmware `UTT2.250416.001` | G08 (MediaTek tcl9618), Google TV 14 | *Settings → System → Power*: network standby | Ethernet, with Wake-on-LAN to the **Ethernet** MAC | HDMI 1: `content://android.media.tv/passthrough/com.tcl.tvinput%2F.TvPassThroughService%2FHW15` | Ignores `KEYCODE_TV_INPUT_HDMI_*` and `SLEEP` (TurnOnTv sends `POWER` when the TV reports on). Pairing reports the Wi-Fi MAC. Switches itself off after a few minutes on an HDMI input with no signal. |

## Input ids from cleanyourtv (not tested with TurnOnTv yet)

The [cleanyourtv](https://github.com/Gathin23/cleanyourtv) project (MIT) documents the TV input services of
some of the models it was run on. Build the URI as `content://android.media.tv/passthrough/<input id>`, with
each `/` written as `%2F`, and test it with `turnontv.py input "<uri>"`. Once one works with TurnOnTv, move it
to the table above.

| TV (cleanyourtv example) | Platform / Android | Input ids |
|---|---|---|
| [TCL G08, Australia](https://github.com/Gathin23/cleanyourtv/tree/main/examples/tcl-g08-au-android12) | G08 (MediaTek), Google TV 12 | HDMI 1: `com.tcl.tvinput/.TvPassThroughService/HW15` |
| [TCL 75P8K](https://github.com/Gathin23/cleanyourtv/tree/main/examples/tcl-75p8k) | G10 (Realtek), Google TV 12 | HDMI 1: `com.tcl.tvinput/.passthroughinput.TvPassThroughService/HW15` |
| [TCL 55C725](https://github.com/Gathin23/cleanyourtv/tree/main/examples/tcl-55c725) | BeyondTV4 / G03 (Realtek), Android TV 11 | Four HDMI inputs: `com.tcl.tvinput/.passthroughinput.TvPassThroughService/` + `HW1413743104`, `HW1413744128`, `HW1413744384`, `HW1413744640` (in that order, port numbers not confirmed) |
| [AQUA MatrixTV EE 50](https://github.com/Gathin23/cleanyourtv/tree/main/examples/aqua-matrixtv-ee-50) | MediaTek (Haier/CVTE), Google TV 14 | HDMI 1-4: `com.mediatek.tis/.HdmiInputService/HW2` to `HW5` |
| [Haier H32S80EFX](https://github.com/Gathin23/cleanyourtv/tree/main/examples/haier-h32s80efx) | MediaTek (CVTE), Google TV 14 | HDMI 1-3: `com.mediatek.tvinput/.hdmi.HDMIInputService/HW5` to `HW7` |

For any other TV, read the ids from the TV once with ADB:
`adb shell dumpsys tv_input | grep -i -E "hdmi|passthrough"` ([PROMPT.md](PROMPT.md), step 6).

## Network standby names by brand

| Brand | Setting |
|---|---|
| Sony | *Remote start* |
| Philips | *Switch on with Wi-Fi (WoWLAN)* |
| TCL | network standby, under *Settings → System → Power* |
| Chromecast with Google TV, Google TV Streamer | stays on the network; no setting needed |

Other brands usually call it "Network standby", "Wake on LAN" or "Wake on Wireless LAN".
