# TurnOnTv for Windows: set up Python, pair with the TV once, and register a scheduled task that wakes the TV
# and switches it to the PC's input whenever you sign in or the PC wakes from sleep.
#
# Usage (from the repository folder, in PowerShell):
#   powershell -ExecutionPolicy Bypass -File windows\install.ps1 -TvHost 192.168.1.50 [-TvInput HDMI_1]
# Run it again at any time: it keeps the pairing and only re-creates the task.
param(
    [string]$TvHost = '',
    [string]$TvInput = 'HDMI_1',
    [string]$InputUri = '',
    [string]$TaskName = 'TurnOnTv'
)
$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
$script = Join-Path $repo 'turnontv.py'
$venv = Join-Path $repo '.venv'
$py = Join-Path $venv 'Scripts\python.exe'
$pyw = Join-Path $venv 'Scripts\pythonw.exe'
$config = Join-Path $env:APPDATA 'TurnOnTv\config.json'

# 1. A private Python environment next to the script.
#    A python.exe under WindowsApps is the Microsoft Store alias, which only prints "Python was not found", and a
#    shell opened before Python was installed (or an SSH session) may not have it on PATH: look in the usual places.
function Find-Python {
    $candidates = @()
    $launcher = Get-Command py -ErrorAction SilentlyContinue
    if ($launcher) {
        $found = & py -3 -c 'import sys; print(sys.executable)' 2>$null
        if ($LASTEXITCODE -eq 0 -and $found) { $candidates += "$found".Trim() }
    }
    $candidates += Get-Command python -All -ErrorAction SilentlyContinue | ForEach-Object Source |
        Where-Object { $_ -notlike '*\WindowsApps\*' }
    foreach ($root in "$env:LOCALAPPDATA\Programs\Python", "$env:ProgramFiles") {
        $candidates += Get-ChildItem $root -Directory -Filter 'Python3*' -ErrorAction SilentlyContinue |
            Sort-Object Name -Descending | ForEach-Object { Join-Path $_.FullName 'python.exe' }
    }
    foreach ($c in $candidates) {
        if (-not (Test-Path $c)) { continue }
        & $c -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' 2>$null
        if ($LASTEXITCODE -eq 0) { return $c }
    }
    return $null
}
if (-not (Test-Path $py)) {
    $base = Find-Python
    if (-not $base) { throw 'Python 3.9 or newer is required: install it from https://www.python.org/downloads/ (or: winget install Python.Python.3.13 --scope user) and run this again.' }
    Write-Host "Using $base"
    & $base -m venv $venv
    if ($LASTEXITCODE -ne 0) { throw 'Could not create the Python environment.' }
}
& $py -m pip install --disable-pip-version-check -q -r (Join-Path $repo 'requirements.txt')
if ($LASTEXITCODE -ne 0) { throw 'Could not install the Python packages.' }

# 2. Pair once. The TV shows a code; type it here.
if (-not (Test-Path $config)) {
    if (-not $TvHost) { throw "Not paired yet: run again with -TvHost <tv ip>." }
    $pairArgs = @($script, "pair", "--host", $TvHost, "--input", $TvInput)
    if ($InputUri) { $pairArgs += @("--input-uri", $InputUri) }
    & $py @pairArgs
    if ($LASTEXITCODE -ne 0) { throw 'Pairing failed.' }
} else {
    Write-Host "Already paired ($config). Delete that folder to pair again."
}

# 3. The scheduled task: at sign-in, and when Windows resumes from sleep or hibernation
#    (System log, Power-Troubleshooter event 1). pythonw runs it without a console window.
#    The account comes from the process token: over SSH, USERDOMAIN reads WORKGROUP and does not resolve.
$account = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$action = New-ScheduledTaskAction -Execute $pyw -Argument "`"$script`" on" -WorkingDirectory $repo
$atLogon = New-ScheduledTaskTrigger -AtLogOn -User $account
$eventClass = Get-CimClass -Namespace Root/Microsoft/Windows/TaskScheduler -ClassName MSFT_TaskEventTrigger
$onResume = New-CimInstance -CimClass $eventClass -ClientOnly -Property @{
    Enabled      = $true
    Subscription = '<QueryList><Query Id="0" Path="System"><Select Path="System">*[System[Provider[@Name=''Microsoft-Windows-Power-Troubleshooter''] and EventID=1]]</Select></Query></QueryList>'
}
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 5) -MultipleInstances IgnoreNew
$principal = New-ScheduledTaskPrincipal -UserId $account -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger @($atLogon, $onResume) -Settings $settings `
    -Principal $principal -Description 'Wake the TV and switch it to this PC (TurnOnTv)' -Force | Out-Null

Write-Host "Installed. The task '$TaskName' runs at sign-in and on wake from sleep."
Write-Host "Try it now with: Start-ScheduledTask -TaskName $TaskName   (log: $env:APPDATA\TurnOnTv\turnontv.log)"
