@echo off
chcp 65001 >nul
setlocal

cd /d "%~dp0"

echo ========================================
echo   AI voice customer service stop tool
echo ========================================
echo.
echo This will close the local RAG backend, NATAPP, and frontend dev windows.
echo.

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\stop-dev.ps1"

echo.
echo Done. You can close this window.
pause
