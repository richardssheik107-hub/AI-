param(
    [string]$NatappToken = "",
    [string]$NatappPath = "$env:USERPROFILE\Downloads\natapp.exe",
    [int]$RagPort = 3001,
    [int]$FrontendPort = 3000
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$RagRoot = Join-Path $ProjectRoot "rag_llm_server"
$PythonExe = Join-Path $RagRoot ".venv\Scripts\python.exe"

function Test-PortListening {
    param([int]$Port)
    $conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    return $null -ne $conn
}

Write-Host "[start-dev] Project root: $ProjectRoot"

if (!(Test-Path $PythonExe)) {
    throw "Python venv not found: $PythonExe"
}

if (!(Test-Path $NatappPath)) {
    throw "NATAPP not found: $NatappPath"
}

if (Test-PortListening $RagPort) {
    Write-Host "[start-dev] RAG backend already listening on port $RagPort"
} else {
    Write-Host "[start-dev] Starting RAG backend on port $RagPort"
    Start-Process powershell.exe -WindowStyle Normal -ArgumentList @(
        "-NoExit",
        "-Command",
        "cd '$RagRoot'; '$PythonExe' -m uvicorn main:app --host 0.0.0.0 --port $RagPort"
    )
}

Write-Host "[start-dev] Starting NATAPP tunnel"
if ($NatappToken) {
    Start-Process powershell.exe -WindowStyle Normal -ArgumentList @(
        "-NoExit",
        "-Command",
        "cd '$(Split-Path $NatappPath)'; & '.\$(Split-Path $NatappPath -Leaf)' -authtoken=$NatappToken"
    )
} else {
    Start-Process powershell.exe -WindowStyle Normal -ArgumentList @(
        "-NoExit",
        "-Command",
        "cd '$(Split-Path $NatappPath)'; & '.\$(Split-Path $NatappPath -Leaf)'"
    )
}

if (Test-PortListening $FrontendPort) {
    Write-Host "[start-dev] Frontend already listening on port $FrontendPort"
} else {
    Write-Host "[start-dev] Starting frontend on port $FrontendPort"
    Start-Process powershell.exe -WindowStyle Normal -ArgumentList @(
        "-NoExit",
        "-Command",
        "cd '$ProjectRoot'; npm run dev"
    )
}

Write-Host ""
Write-Host "[start-dev] Open frontend: http://localhost:$FrontendPort"
Write-Host "[start-dev] Inspect tunnel: http://127.0.0.1:4040"
Write-Host "[start-dev] RAG health: http://localhost:$RagPort/health"
Write-Host ""
Write-Host "If NATAPP prints a new public URL, update rag_llm_server\.env SERVER_URL and restart the RAG backend window."
