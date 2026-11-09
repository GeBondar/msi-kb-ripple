@echo off
rem Stops whichever background effect is running (ripple or fire) and sets the keyboard to white.
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='pythonw.exe'\" | Where-Object CommandLine -match '(ripple|fire)\.py' | ForEach-Object { Stop-Process -Id $_.ProcessId }"
cd /d "%~dp0"
python -c "from msikb import Kb; Kb().static(0xFFFFFF,(255,255,255))"
echo Effect stopped.
