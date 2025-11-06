# PowerShell launcher for VendAI desktop (Windows)
# Starts Odoo in background, waits for HTTP endpoint, then opens the webview app.

$root = Split-Path -Parent $PSScriptRoot
$python = "$(Get-Command python).Source"

Write-Host "Starting Odoo (background)..."
Start-Process -FilePath $python -ArgumentList "`"$root\..\odoo-bin`" -c `"$root\..\config\odoo.conf`" -d vendai_db --http-port=8069" -WindowStyle Hidden

# Wait for HTTP
$uri = 'http://localhost:8069'
$timeout = 60
$start = Get-Date
Write-Host "Waiting for Odoo to respond at $uri"
while ((Get-Date) - $start).TotalSeconds -lt $timeout {
    try {
        $r = Invoke-WebRequest -Uri $uri -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
        Write-Host "Odoo responded: $($r.StatusCode)"
        break
    } catch {
        Start-Sleep -Seconds 1
    }
}

if ((Get-Date) - $start).TotalSeconds -ge $timeout {
    Write-Host "Timeout waiting for Odoo. Please start Odoo manually and then run the app." -ForegroundColor Yellow
    exit 1
}

Write-Host "Launching VendAI desktop app..."
Start-Process -FilePath $python -ArgumentList "`"$root\app.py`"" -NoNewWindow
