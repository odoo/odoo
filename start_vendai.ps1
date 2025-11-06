#!/usr/bin/env powershell
# VendAI Finance - Odoo Quick Start Script

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "   VendAI Finance - Odoo Module Installation" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""

# Configuration
$ODOO_PATH = "C:\Users\lided\projects\odoo"
$DB_NAME = "vendai_demo"
$ADMIN_PASSWORD = "admin"
$PORT = 8069

Write-Host "Step 1: Checking Odoo installation..." -ForegroundColor Yellow
if (-not (Test-Path "$ODOO_PATH\odoo-bin")) {
    Write-Host "ERROR: odoo-bin not found at $ODOO_PATH" -ForegroundColor Red
    exit 1
}
Write-Host "✓ Odoo found at: $ODOO_PATH" -ForegroundColor Green
Write-Host ""

Write-Host "Step 2: Checking VendAI Finance module..." -ForegroundColor Yellow
if (-not (Test-Path "$ODOO_PATH\addons\vendai_finance\__manifest__.py")) {
    Write-Host "ERROR: VendAI Finance module not found in addons" -ForegroundColor Red
    exit 1
}
Write-Host "✓ VendAI Finance module found" -ForegroundColor Green
Write-Host ""

Write-Host "Step 3: Starting Odoo..." -ForegroundColor Yellow
Write-Host "Database: $DB_NAME" -ForegroundColor Cyan
Write-Host "Port: $PORT" -ForegroundColor Cyan
Write-Host "Module: vendai_finance" -ForegroundColor Cyan
Write-Host ""

# Change to Odoo directory
Set-Location $ODOO_PATH

# Activate virtual environment if it exists
if (Test-Path ".\venv\Scripts\Activate.ps1") {
    Write-Host "Activating Python virtual environment..." -ForegroundColor Yellow
    & .\venv\Scripts\Activate.ps1
    Write-Host "✓ Virtual environment activated" -ForegroundColor Green
    Write-Host ""
}

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "Starting Odoo Server..." -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Once Odoo starts, open your browser to:" -ForegroundColor Yellow
Write-Host "http://localhost:$PORT" -ForegroundColor Green
Write-Host ""
Write-Host "Then:" -ForegroundColor Yellow
Write-Host "1. Create new database '$DB_NAME' (or use existing)" -ForegroundColor White
Write-Host "2. Go to Apps menu" -ForegroundColor White
Write-Host "3. Remove 'Apps' filter" -ForegroundColor White
Write-Host "4. Click 'Update Apps List'" -ForegroundColor White
Write-Host "5. Search for 'VendAI'" -ForegroundColor White
Write-Host "6. Click Install" -ForegroundColor White
Write-Host ""
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host ""

# Start Odoo
python odoo-bin -d $DB_NAME --addons-path=addons --db-filter=^$DB_NAME$ -i vendai_finance
