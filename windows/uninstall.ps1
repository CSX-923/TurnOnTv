# Remove the TurnOnTv scheduled task. Add -Forget to also delete the pairing and settings in %APPDATA%\TurnOnTv.
# Usage: powershell -ExecutionPolicy Bypass -File windows\uninstall.ps1 [-Forget]
param(
    [switch]$Forget,
    [string]$TaskName = 'TurnOnTv'
)
$ErrorActionPreference = 'Stop'
if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "Removed the task '$TaskName'."
} else {
    Write-Host "No task named '$TaskName'."
}
if ($Forget) {
    Remove-Item -Recurse -Force (Join-Path $env:APPDATA 'TurnOnTv') -ErrorAction SilentlyContinue
    Write-Host 'Deleted the pairing and settings. The TV may still list this computer as a paired remote.'
}
