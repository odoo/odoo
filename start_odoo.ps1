# Start Odoo with wkhtmltopdf available for PDF reports
$wkhtmlBin = "C:\Program Files\wkhtmltopdf\bin"
if (Test-Path $wkhtmlBin) {
    $env:Path = "$wkhtmlBin;$env:Path"
}

Set-Location $PSScriptRoot
& .\venv\Scripts\python.exe .\odoo-bin -c .\odoo.conf @args
