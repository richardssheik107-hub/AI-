@echo off
chcp 65001 >nul
setlocal

cd /d "%~dp0"

echo ========================================
echo  AI voice customer service dev launcher
echo ========================================
echo.
echo This will open RAG backend, NATAPP, and frontend windows.
echo If NATAPP has already saved your token, press Enter directly.
echo.

set /p NATAPP_TOKEN=Enter NATAPP token (optional): 

if "%NATAPP_TOKEN%"=="" (
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start-dev.ps1"
) else (
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start-dev.ps1" -NatappToken "%NATAPP_TOKEN%"
)

echo.
echo Done. You can close this window.
pause
