# Removes autostart, stops the background effect (ripple or fire) and sets the keyboard to white.
# Usage:  powershell -ExecutionPolicy Bypass -File uninstall.ps1
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$lnk = Join-Path ([Environment]::GetFolderPath('Startup')) 'MSI Keyboard Ripple.lnk'
if (Test-Path $lnk) { Remove-Item $lnk; Write-Host "Removed $lnk" }
& (Join-Path $here 'stop-ripple.cmd')
