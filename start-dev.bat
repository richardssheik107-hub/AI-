@echo off
chcp 65001 >nul
setlocal

cd /d "%~dp0"

echo ========================================
echo  AI voice customer service dev launcher
echo ========================================
echo.
echo This will open RAG backend, NATAPP, and frontend windows.
echo If NATAPP_TOKEN is set in rag_llm_server\.env, the launcher will use it automatically.
echo.

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start-dev.ps1"

echo.
echo Done. You can close this window.
pause
