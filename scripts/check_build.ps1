param(
    [string]$ExePath = ".\PathCopy.exe"
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path $PSScriptRoot -Parent
Push-Location $RepoRoot

try {
    $ResolvedExe = Resolve-Path -LiteralPath $ExePath -ErrorAction Stop
    $Item = Get-Item -LiteralPath $ResolvedExe

    if ($Item.Length -lt 1MB) {
        throw "PathCopy.exe looks too small: $($Item.Length) bytes"
    }

    $Version = [System.Diagnostics.FileVersionInfo]::GetVersionInfo($ResolvedExe)
    if ($Version.ProductName -ne "PathCopy") {
        throw "Unexpected ProductName in exe version info: $($Version.ProductName)"
    }

    Write-Host "PathCopy build check passed:"
    Write-Host "  $ResolvedExe"
    Write-Host "  Size   : $([math]::Round($Item.Length / 1MB, 2)) MB"
    Write-Host "  Version: $($Version.ProductVersion)"
}
finally {
    Pop-Location
}
