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
$EnvFile = Join-Path $RagRoot ".env"
$NatappTokenKey = "NATAPP_TOKEN"

function Test-PortListening {
    param([int]$Port)
    $conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    return $null -ne $conn
}

function Wait-ForPortListening {
    param(
        [int]$Port,
        [int]$TimeoutSeconds = 12
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if (Test-PortListening $Port) {
            return $true
        }
        Start-Sleep -Milliseconds 500
    }

    return (Test-PortListening $Port)
}

function Test-HttpOk {
    param(
        [string]$Url,
        [int]$TimeoutSeconds = 5
    )

    try {
        $response = Invoke-WebRequest -Method Get -Uri $Url -UseBasicParsing -TimeoutSec $TimeoutSeconds
        return ($response.StatusCode -ge 200 -and $response.StatusCode -lt 400)
    } catch {
        return $false
    }
}

function Get-EnvValue {
    param(
        [string]$FilePath,
        [string]$Key
    )

    if (!(Test-Path $FilePath)) {
        return $null
    }

    $match = Get-Content -Path $FilePath | Where-Object {
        $_ -match "^\s*$Key\s*="
    } | Select-Object -First 1

    if ($null -eq $match) {
        return $null
    }

    return (($match -split "=", 2)[1]).Trim()
}

Write-Host "[start-dev] Project root: $ProjectRoot"

if (!(Test-Path $PythonExe)) {
    throw "Python venv not found: $PythonExe"
}

if (!(Test-Path $NatappPath)) {
    throw "NATAPP not found: $NatappPath"
}

if (-not $NatappToken) {
    $NatappToken = Get-EnvValue -FilePath $EnvFile -Key $NatappTokenKey
    if ($NatappToken) {
        Write-Host "[start-dev] Loaded NATAPP token from rag_llm_server\.env"
    }
}

if (Test-PortListening $RagPort) {
    Write-Host "[start-dev] RAG backend already listening on port $RagPort"
} else {
    Write-Host "[start-dev] Starting RAG backend on port $RagPort"
    Start-Process powershell.exe -WindowStyle Normal -ArgumentList @(
        "-NoExit",
        "-Command",
        "cd '$RagRoot'; & '$PythonExe' -m uvicorn main:app --host 0.0.0.0 --port $RagPort"
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
Write-Host ""
Write-Host "[start-dev] Running quick self-check..."

$frontendReady = Wait-ForPortListening -Port $FrontendPort
$ragReady = Wait-ForPortListening -Port $RagPort
$ragHealthOk = $false
$natappUiOk = $false
$publicHealthOk = $false
$serverUrl = Get-EnvValue -FilePath $EnvFile -Key "SERVER_URL"

if ($ragReady) {
    $ragHealthOk = Test-HttpOk -Url "http://localhost:$RagPort/health"
}

$natappUiOk = Test-HttpOk -Url "http://127.0.0.1:4040"

if ($serverUrl) {
    $publicHealthOk = Test-HttpOk -Url ($serverUrl.TrimEnd("/") + "/health")
}

Write-Host ("[start-dev] Frontend port {0}: {1}" -f $FrontendPort, ($(if ($frontendReady) { "OK" } else { "NOT READY" })))
Write-Host ("[start-dev] RAG port {0}: {1}" -f $RagPort, ($(if ($ragReady) { "OK" } else { "NOT READY" })))
Write-Host ("[start-dev] RAG health: {0}" -f ($(if ($ragHealthOk) { "OK" } else { "FAILED" })))
Write-Host ("[start-dev] NATAPP inspect UI: {0}" -f ($(if ($natappUiOk) { "OK" } else { "FAILED" })))
if ($serverUrl) {
    Write-Host ("[start-dev] SERVER_URL in .env: {0}" -f $serverUrl)
    Write-Host ("[start-dev] Public health: {0}" -f ($(if ($publicHealthOk) { "OK" } else { "FAILED" })))
}

if (-not $natappUiOk) {
    Write-Host ""
    Write-Host "[start-dev] NATAPP inspection page did not come up yet."
    Write-Host "[start-dev] Before starting a voice call, check the NATAPP window and confirm http://127.0.0.1:4040 can open."
}

if ($serverUrl -and -not $publicHealthOk) {
    Write-Host ""
    Write-Host "[start-dev] Public callback check failed."
    Write-Host "[start-dev] Confirm that NATAPP is online and that SERVER_URL matches the latest public address."
}
