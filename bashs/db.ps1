# Create an Odoo database pre-loaded with a named "bouquet" of modules.
#
# Usage:
#   .\bashs\db.ps1 <database> [bouquet] [-NoDemo]
#   .\bashs\db.ps1 -List
#
# Examples:
#   .\bashs\db.ps1 pos_test    pos
#   .\bashs\db.ps1 sales_test  main
#   .\bashs\db.ps1 factory     mrp
#   .\bashs\db.ps1 everything  full          # all application=True, no l10n_*
#   .\bashs\db.ps1 clean       main -NoDemo  # skip demo data

param(
    [Parameter(Position = 0)]
    [string]$Database,

    [Parameter(Position = 1)]
    [string]$Bouquet = "main",

    [switch]$NoDemo,

    [switch]$List
)

$ErrorActionPreference = "Stop"

$pythonExe  = ".\venv\Scripts\python.exe"
$configFile = ".\config\odoo.conf"

# Installed in EVERY database regardless of bouquet, so each DB carries its
# own System Configuration admin panel (db type, limits, bouquet).
$alwaysInstall = "system_config"

# --- Bouquet presets ------------------------------------------------------
# Edit freely. Odoo pulls in each module's dependencies automatically.
# "full" is special: it installs every application module except localizations.
$bouquets = [ordered]@{
    "min"  = "base"
    "main" = "crm,sale_management,stock,account,contacts,calendar"
    "pos"  = "point_of_sale"
    "mrp"  = "mrp,stock,purchase"
    "full" = "*"
}

function Show-Bouquets {
    Write-Host "Available bouquets:" -ForegroundColor Cyan
    foreach ($key in $bouquets.Keys) {
        $val = if ($bouquets[$key] -eq "*") { "all application modules (no l10n_*)" } else { $bouquets[$key] }
        Write-Host ("  {0,-6} {1}" -f $key, $val)
    }
}

if ($List) {
    Show-Bouquets
    exit 0
}

# --- Validation -----------------------------------------------------------
if (-not $Database) {
    Write-Error "Missing database name.  Usage: .\bashs\db.ps1 <database> [bouquet] [-NoDemo]"
    Show-Bouquets
    exit 1
}

if (-not $bouquets.Contains($Bouquet)) {
    Write-Error "Unknown bouquet '$Bouquet'."
    Show-Bouquets
    exit 1
}

if (-not (Test-Path $pythonExe))  { Write-Error "virtualenv not found at $pythonExe";  exit 1 }
if (-not (Test-Path $configFile)) { Write-Error "config file not found at $configFile"; exit 1 }

$demoArgs = @()
if ($NoDemo) { $demoArgs = @("--without-demo=all") }

Write-Host "Creating database '$Database' with bouquet '$Bouquet'..." -ForegroundColor Green

if ($bouquets[$Bouquet] -eq "*") {
    # --- full: create the DB, then install every application module (no l10n) ---
    Write-Host "Step 1/2: initializing base + system config..." -ForegroundColor Yellow
    & $pythonExe odoo-bin -c $configFile -d $Database -i "base,$alwaysInstall" --stop-after-init @demoArgs
    if ($LASTEXITCODE -ne 0) { Write-Error "base init failed (exit $LASTEXITCODE)"; exit $LASTEXITCODE }

    Write-Host "Step 2/2: installing all application modules (excluding localizations)..." -ForegroundColor Yellow
    $snippet = @'
apps = env['ir.module.module'].search([
    ('state', '=', 'uninstalled'),
    ('application', '=', True),
    ('country_ids', '=', False),
])
print('Installing:', ', '.join(sorted(apps.mapped('name'))) or '(nothing new)')
if apps:
    apps.button_immediate_install()
    env.cr.commit()
'@
    $snippet | & $pythonExe odoo-bin shell -c $configFile -d $Database --no-http
    if ($LASTEXITCODE -ne 0) { Write-Error "app install failed (exit $LASTEXITCODE)"; exit $LASTEXITCODE }
}
else {
    $modules = "$($bouquets[$Bouquet]),$alwaysInstall"
    Write-Host "Installing: $modules" -ForegroundColor Yellow
    & $pythonExe odoo-bin -c $configFile -d $Database -i $modules --stop-after-init @demoArgs
    if ($LASTEXITCODE -ne 0) { Write-Error "install failed (exit $LASTEXITCODE)"; exit $LASTEXITCODE }
}

Write-Host ""
Write-Host "Done. Database '$Database' is ready." -ForegroundColor Green
Write-Host "Start it with:  .\bashs\start-odoo.ps1   then open http://localhost:8069" -ForegroundColor Cyan
