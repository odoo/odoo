# Start Odoo server with dev helpers (autoreload, qweb, werkzeug, xml)

$ErrorActionPreference = "Stop"

$pythonExe = ".\venv\Scripts\python.exe"
$configFile = ".\config\odoo.conf"

if (-not (Test-Path $pythonExe)) {
    Write-Error "Error: virtualenv not found at $pythonExe"
    exit 1
}

if (-not (Test-Path $configFile)) {
    Write-Error "Error: config file not found at $configFile"
    exit 1
}

Write-Host "Starting Odoo server..." -ForegroundColor Green
Write-Host "Access at http://localhost:8069" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop" -ForegroundColor Yellow
Write-Host ""

& $pythonExe odoo-bin -c $configFile --dev=reload,qweb,werkzeug,xml
