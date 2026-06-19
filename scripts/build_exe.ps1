param(
    [switch]$InstallDependencies,
    [switch]$Clean,
    [ValidateSet("onefile", "onedir")]
    [string]$Mode = "onefile"
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path $PSScriptRoot -Parent
Push-Location $RepoRoot

try {
    Write-Host "[PathCopy] Repo: $RepoRoot"

    # 1) Check python availability
    $pyOut = & python --version 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "python not found on PATH. Please install Python 3.10+ and add it to PATH. Output was: $pyOut"
    }

    # 2) Install dependencies
    if ($InstallDependencies) {
        Write-Host "[PathCopy] Installing dependencies..."
        & python -m pip install -r requirements.txt
        if ($LASTEXITCODE -ne 0) { throw "pip install failed" }
    }
    else {
        # Make sure PyInstaller is available even when -InstallDependencies is not set
        & python -m PyInstaller --version | Out-Null
        if ($LASTEXITCODE -ne 0) {
            throw "PyInstaller not found. Re-run with -InstallDependencies, or run: python -m pip install -r requirements.txt"
        }
    }

    # 3) Clean old artifacts
    if ($Clean) {
        Write-Host "[PathCopy] Cleaning old artifacts..."
        Remove-Item -LiteralPath (Join-Path $RepoRoot "build") -Recurse -Force -ErrorAction SilentlyContinue
        Remove-Item -LiteralPath (Join-Path $RepoRoot "dist") -Recurse -Force -ErrorAction SilentlyContinue
    }

    # 4) Build with PyInstaller
    $Spec = ".\PathCopy.spec"
    Write-Host "[PathCopy] Running PyInstaller ($Mode)..."
    & python -m PyInstaller --clean --noconfirm $Spec
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }

    # 5) Verify the artifact exists
    $Exe = Join-Path $RepoRoot "dist\PathCopy.exe"
    if (-not (Test-Path $Exe)) {
        throw "Build finished but PathCopy.exe was not found at $Exe"
    }

    # 6) Copy to repo root (requirement: final output is a single exe in the repo root)
    $RootExe = Join-Path $RepoRoot "PathCopy.exe"
    Copy-Item -LiteralPath $Exe -Destination $RootExe -Force

    Write-Host ""
    Write-Host "[PathCopy] Build OK."
    Write-Host "  dist exe : $Exe"
    Write-Host "  root exe : $RootExe"
}
finally {
    Pop-Location
}
