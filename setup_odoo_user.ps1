# PowerShell script to create Odoo database user
# This script will prompt you for the postgres password

$pgBin = "C:\Program Files\PostgreSQL\16\bin\psql.exe"

Write-Host "=== Creating Odoo Database User ===" -ForegroundColor Green
Write-Host ""
Write-Host "This script will create a database user named 'odoo' with password 'odoo'"
Write-Host "You'll be prompted for the 'postgres' user password (the one you set during installation)"
Write-Host ""

# Check if psql exists
if (-not (Test-Path $pgBin)) {
    Write-Host "ERROR: PostgreSQL not found at $pgBin" -ForegroundColor Red
    Write-Host "Please check your PostgreSQL installation path." -ForegroundColor Red
    exit 1
}

Write-Host "Connecting to PostgreSQL..." -ForegroundColor Yellow
Write-Host ""

# Create the SQL commands
$sqlCommands = @"
-- Create Odoo user
CREATE USER odoo WITH PASSWORD 'odoo';

-- Grant permission to create databases
ALTER USER odoo CREATEDB;

-- Verify user was created
\du odoo
"@

# Save SQL to temp file
$tempSql = [System.IO.Path]::GetTempFileName() + ".sql"
$sqlCommands | Out-File -FilePath $tempSql -Encoding UTF8

try {
    # Run psql with the SQL file
    # Note: This will prompt for password
    & $pgBin -U postgres -f $tempSql
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "SUCCESS! Odoo user created successfully!" -ForegroundColor Green
        Write-Host ""
        Write-Host "User details:" -ForegroundColor Cyan
        Write-Host "  Username: odoo" -ForegroundColor White
        Write-Host "  Password: odoo" -ForegroundColor White
        Write-Host ""
        Write-Host "Next step: Update odoo.conf with these credentials" -ForegroundColor Yellow
    } else {
        Write-Host ""
        Write-Host "ERROR: Failed to create user. Please check the error messages above." -ForegroundColor Red
    }
} catch {
    Write-Host ""
    Write-Host "ERROR: $($_.Exception.Message)" -ForegroundColor Red
} finally {
    # Clean up temp file
    if (Test-Path $tempSql) {
        Remove-Item $tempSql -Force -ErrorAction SilentlyContinue
    }
}
