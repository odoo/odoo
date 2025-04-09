@echo off
SET ODOO_CONTAINER_NAME=odoo
SET ODOO_IMAGE_NAME=odoo
SET DB_CONTAINER_NAME=postgres
SET DB_IMAGE_NAME=postgres:15
SET DB_VOLUME_NAME=pgdata

REM Stop and remove any running Odoo container
docker ps -q -f name=%ODOO_CONTAINER_NAME% >nul 2>nul
IF NOT ERRORLEVEL 1 (
    echo Stopping the running '%ODOO_CONTAINER_NAME%' container...
    docker stop %ODOO_CONTAINER_NAME%
    docker rm %ODOO_CONTAINER_NAME%
)

REM Stop and remove any running PostgreSQL container
docker ps -q -f name=%DB_CONTAINER_NAME% >nul 2>nul
IF NOT ERRORLEVEL 1 (
    echo Stopping the running '%DB_CONTAINER_NAME%' container...
    docker stop %DB_CONTAINER_NAME%
    docker rm %DB_CONTAINER_NAME%
)

REM Remove previous Odoo image
docker images -q %ODOO_IMAGE_NAME% >nul 2>nul
IF NOT ERRORLEVEL 1 (
    echo Removing the previous '%ODOO_IMAGE_NAME%' Docker image...
    docker rmi %ODOO_IMAGE_NAME%
)

echo Creating Docker volume for PostgreSQL...
docker volume create %DB_VOLUME_NAME%

echo Running PostgreSQL container...
docker run -d ^
    --name %DB_CONTAINER_NAME% ^
    -e POSTGRES_DB=postgres ^
    -e POSTGRES_USER=odoo ^
    -e POSTGRES_PASSWORD=myodoo ^
    -v %DB_VOLUME_NAME%:/var/lib/postgresql/data ^
    postgres:15

echo Building the Odoo Docker image...
docker build -t %ODOO_IMAGE_NAME% .
IF ERRORLEVEL 1 (
    echo Docker build failed. Exiting.
    exit /b 1
)

echo Docker image built successfully.

echo Running the Odoo container...
docker run -d ^
    --name %ODOO_CONTAINER_NAME% ^
    --link %DB_CONTAINER_NAME%:db ^
    -p 8069:8069 ^
    -v odoo-data:/var/lib/odoo ^
    -v "%CD%/addons":/mnt/extra-addons ^
    -v "%CD%/custom_addons":/mnt/custom-addons ^
    -e HOST=db ^
    -e USER=odoo ^
    -e PASSWORD=myodoo ^
    %ODOO_IMAGE_NAME%

echo Opening http://localhost:8069 in the browser...
start http://localhost:8069
