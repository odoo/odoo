param(
    [string]$Config = "kore.conf",
    [string]$Db = "kore",
    [string]$LogPath = "logs/odoo-lnav.log"
)

if(-not (Test-Path (Split-Path $LogPath))) {
    New-Item -ItemType Directory -Path (Split-Path $LogPath) | Out-Null
}

$python = Resolve-Path "venv\\Scripts\\python.exe"
$odoo = Resolve-Path "odoo-bin"

Write-Host "Starting Odoo ($Db) -> $LogPath"
Start-Process -NoNewWindow -FilePath $python -ArgumentList "$odoo -c $Config -d $Db --logfile=$LogPath --log-level=info"

Write-Host "Launching lnav on $LogPath"
Start-Process -FilePath "lnav" -ArgumentList $LogPath
