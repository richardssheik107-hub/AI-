param(
    [int]$RagPort = 3001,
    [int]$FrontendPort = 3000,
    [switch]$Preview
)

$ErrorActionPreference = "Stop"

function Get-ListeningProcessIds {
    param([int]$Port)

    $connections = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    if ($null -eq $connections) {
        return @()
    }

    return @($connections | Select-Object -ExpandProperty OwningProcess -Unique)
}

function Stop-ProcessByIdSafe {
    param(
        [int]$ProcessId,
        [string]$Reason
    )

    if ($ProcessId -le 0) {
        return
    }

    $proc = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
    if ($null -eq $proc) {
        return
    }

    if ($Preview) {
        Write-Host "[stop-dev] Preview: would stop PID $ProcessId ($($proc.ProcessName)) - $Reason"
        return
    }

    Write-Host "[stop-dev] Stopping PID $ProcessId ($($proc.ProcessName)) - $Reason"
    Stop-Process -Id $ProcessId -Force -ErrorAction SilentlyContinue
}

function Stop-PowershellWindowsByPattern {
    param(
        [string[]]$Patterns,
        [string]$Reason
    )

    $psProcesses = Get-CimInstance Win32_Process |
        Where-Object {
            ($_.Name -in @("powershell.exe", "pwsh.exe")) -and
            $_.CommandLine
        }

    foreach ($proc in $psProcesses) {
        $commandLine = [string]$proc.CommandLine
        $matched = $false
        foreach ($pattern in $Patterns) {
            if ($commandLine -like "*$pattern*") {
                $matched = $true
                break
            }
        }

        if ($matched) {
            Stop-ProcessByIdSafe -ProcessId ([int]$proc.ProcessId) -Reason $Reason
        }
    }
}

Write-Host "[stop-dev] Closing local dev services..."

$ragPids = Get-ListeningProcessIds -Port $RagPort
if ($ragPids.Count -eq 0) {
    Write-Host "[stop-dev] No process is listening on port $RagPort"
} else {
    foreach ($targetPid in $ragPids) {
        Stop-ProcessByIdSafe -ProcessId $targetPid -Reason "RAG backend port $RagPort"
    }
}

$frontendPids = Get-ListeningProcessIds -Port $FrontendPort
if ($frontendPids.Count -eq 0) {
    Write-Host "[stop-dev] No process is listening on port $FrontendPort"
} else {
    foreach ($targetPid in $frontendPids) {
        Stop-ProcessByIdSafe -ProcessId $targetPid -Reason "Frontend port $FrontendPort"
    }
}

$natappProcesses = Get-Process -Name "natapp" -ErrorAction SilentlyContinue
if ($null -eq $natappProcesses) {
    Write-Host "[stop-dev] No natapp.exe process found"
} else {
    foreach ($proc in $natappProcesses) {
        Stop-ProcessByIdSafe -ProcessId $proc.Id -Reason "NATAPP tunnel"
    }
}

Stop-PowershellWindowsByPattern -Patterns @(
    "uvicorn main:app --host 0.0.0.0 --port $RagPort",
    "npm run dev",
    "natapp.exe"
) -Reason "launcher window cleanup"

Write-Host "[stop-dev] Done."
Write-Host "[stop-dev] You can now run start-dev.bat for a clean restart."
