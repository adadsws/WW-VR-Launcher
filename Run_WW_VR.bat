@echo off
:: Check if running as administrator
net session >nul 2>&1
if %errorLevel% == 0 (
    echo Administrator privileges confirmed.
) else (
    echo Requesting Master Privileges...
    echo Set UAC = CreateObject^("Shell.Application"^) > "%temp%\getadmin.vbs"
    echo UAC.ShellExecute "%~s0", "", "", "runas", 1 >> "%temp%\getadmin.vbs"
    "%temp%\getadmin.vbs"
    del "%temp%\getadmin.vbs"
    exit /B
)

:: Change director to the batch file's directory
cd /d "%~dp0src"

echo Installing required packages...
pip install -r ..\requirements.txt

echo Starting WW VR Launcher (UEVR)...
python ww_vr_launcher.py

pause
