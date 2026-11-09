# Installs msi-kb-ripple for the current user:
#   1. pip-installs hidapi   2. checks the MysticLight controller is present
#   3. adds a Startup shortcut (pythonw, no window)   4. starts it now
# Usage:  powershell -ExecutionPolicy Bypass -File install.ps1 [-Effect ripple|fire]
# Re-running with another -Effect switches the autostarted effect.
param([ValidateSet('ripple', 'fire')][string]$Effect = 'ripple')
$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = (Get-Command python -ErrorAction Stop).Source
$pythonw = Join-Path (Split-Path $python) 'pythonw.exe'
if (-not (Test-Path $pythonw)) { throw "pythonw.exe not found next to $python" }

& $python -m pip install --quiet -r (Join-Path $here 'requirements.txt')

$found = & $python -c "import hid; print(len(hid.enumerate(0x1462, 0x1603)))"
if ([int]$found -lt 1) {
    throw "MysticLight controller 1462:1603 not found. This build targets MSI laptops with that controller - see AGENTS.md before trying anything else."
}

& (Join-Path $here 'stop-ripple.cmd') | Out-Null    # only one effect can drive the LEDs

$lnk = Join-Path ([Environment]::GetFolderPath('Startup')) 'MSI Keyboard Ripple.lnk'
$s = (New-Object -ComObject WScript.Shell).CreateShortcut($lnk)
$s.TargetPath = $pythonw
$s.Arguments = '"' + (Join-Path $here "$Effect.py") + '"'
$s.WorkingDirectory = $here
$s.Description = "Keyboard lighting: $Effect"
$s.Save()

Start-Process $pythonw -ArgumentList $s.Arguments -WorkingDirectory $here
Write-Host "Installed '$Effect'. Autostart: $lnk"
Write-Host "Type something and watch the keyboard."
