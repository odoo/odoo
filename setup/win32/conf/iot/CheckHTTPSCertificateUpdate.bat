echo Odoo IoT HTTPS Certificate Update Check...
@echo off

set url=http://localhost:8069/hw_drivers/check_certificate
set curl_command=curl -s -o nul -w %%{http_code} %url%

for /f %%i in ('%curl_command%') do set http_status=%%i

if %http_status% equ 200 (
    exit /b 0
) else (
    exit /b 1
)
