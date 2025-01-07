
$BUILD_FOLDER = "C:/odoobuild"

$GIT_EXEC_PATH = "$BUILD_FOLDER/git/cmd/git.exe"
$GIT_ODOO_VERSION = "18.0"
$GIT_REPO_URL = "https://github.com/lse-odoo/odoo.git"

$APP_FOLDER_NAME = "server"
$APP_FOLDER_PATH = "$BUILD_FOLDER/$APP_FOLDER_NAME"

# Remove the app folder if existing then create it
If (Test-Path $APP_FOLDER_PATH) {
    Remove-Item $APP_FOLDER_PATH -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $BUILD_FOLDER -Name $APP_FOLDER_NAME

# Create the git repository. Load as less stuff as possible as only certain folder interest us
Start-Process -FilePath "$GIT_EXEC_PATH" -ArgumentList "-C $APP_FOLDER_PATH clone -b $GIT_ODOO_VERSION --no-local --no-checkout --depth 1 $GIT_REPO_URL ." -Wait -NoNewWindow
Start-Process -FilePath "$GIT_EXEC_PATH" -ArgumentList "-C $APP_FOLDER_PATH/odoo config core.sparsecheckout true" -Wait -NoNewWindow
New-Item -ItemType File -Force -Path $APP_FOLDER_PATH/odoo/.git/info/sparse-checkout -Value @"
/odoo-bin
/odoo/
/addons/web
/addons/hw_*
"@
# / at the beginning is needed otherwise we end up having undesired paths like
# ./app/odoo/addons/point_of_sale/tools/posbox/overwrite_after_init/home/pi/odoo/addons/point_of_sale/__manifest__.py
# because they do contains "odoo/"
Start-Process -FilePath "$GIT_EXEC_PATH" -ArgumentList "-C $APP_FOLDER_PATH/odoo read-tree -mu HEAD" -Wait -NoNewWindow

Write-Host "Finished!"
