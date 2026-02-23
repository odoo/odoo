#!/bin/bash
# =============================================================================
# Script de instalación de Odoo en Raspberry Pi 5 (8 GB RAM)
# Sistema Operativo: Ubuntu Server 24.04 LTS (arm64)
#
# Uso:
#   chmod +x install_odoo_rpi5.sh
#   sudo bash install_odoo_rpi5.sh
#
# Este script realiza los siguientes pasos:
#   1. Actualiza la distribución de Ubuntu
#   2. Instala todos los paquetes requeridos para Odoo
#   3. Instala y configura PostgreSQL
#   4. Clona el repositorio completo de Odoo
#   5. Configura e inicia Odoo
# =============================================================================

set -e

# --- Configuración -----------------------------------------------------------
ODOO_USER="odoo"
ODOO_HOME="/opt/odoo"
ODOO_REPO="https://github.com/odoo/odoo.git"
ODOO_BRANCH="18.0"
ODOO_DIR="${ODOO_HOME}/odoo"
ODOO_CONF="/etc/odoo/odoo.conf"
ODOO_LOG_DIR="/var/log/odoo"

# --- Colores para mensajes ---------------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # Sin color

log_info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# --- Verificar ejecución como root -------------------------------------------
if [ "$(id -u)" -ne 0 ]; then
    log_error "Este script debe ejecutarse como root (usa: sudo bash $0)"
    exit 1
fi

# =============================================================================
# PASO 1: Actualizar la distribución de Ubuntu
# =============================================================================
log_info "Paso 1/6: Actualizando la distribución de Ubuntu..."
apt-get update
apt-get upgrade -y
apt-get dist-upgrade -y
dpkg --configure -a
apt-get --fix-broken install -y
apt-get clean
apt-get update
log_info "Sistema actualizado correctamente."

# =============================================================================
# PASO 2: Instalar paquetes base del sistema
# =============================================================================
log_info "Paso 2/6: Instalando paquetes base del sistema..."
apt-get install -y --no-install-recommends \
    git \
    python3-full \
    python3-pip \
    python3-venv \
    build-essential \
    wget \
    curl \
    libldap2-dev \
    libsasl2-dev \
    libpq-dev \
    libjpeg-dev \
    zlib1g-dev \
    libfreetype6-dev \
    liblcms2-dev \
    libwebp-dev \
    libtiff5-dev \
    libxml2-dev \
    libxslt1-dev \
    libffi-dev \
    nodejs \
    npm \
    wkhtmltopdf

log_info "Paquetes base instalados correctamente."

# =============================================================================
# PASO 3: Instalar dependencias de Python y fuentes para Odoo
# =============================================================================
log_info "Paso 3/6: Instalando dependencias de Python y fuentes para Odoo..."
apt-get install -y --no-install-recommends \
    python3-asn1crypto \
    python3-babel \
    python3-cbor2 \
    python3-chardet \
    python3-cryptography \
    python3-dateutil \
    python3-docutils \
    python3-freezegun \
    python3-geoip2 \
    python3-gevent \
    python3-greenlet \
    python3-idna \
    python3-pil \
    python3-jinja2 \
    python3-libsass \
    python3-lxml \
    python3-lxml-html-clean \
    python3-magic \
    python3-markupsafe \
    python3-num2words \
    python3-ofxparse \
    python3-openpyxl \
    python3-passlib \
    python3-polib \
    python3-psutil \
    python3-psycopg2 \
    python3-openssl \
    python3-pypdf2 \
    python3-rjsmin \
    python3-qrcode \
    python3-renderpm \
    python3-reportlab \
    python3-requests \
    python3-stdnum \
    python3-tz \
    python3-urllib3 \
    python3-vobject \
    python3-werkzeug \
    python3-xlsxwriter \
    python3-xlrd \
    python3-zeep \
    fonts-dejavu-core \
    fonts-inconsolata \
    fonts-font-awesome \
    fonts-roboto-unhinted \
    gsfonts

log_info "Dependencias de Python y fuentes instaladas correctamente."

# =============================================================================
# PASO 4: Instalar y configurar PostgreSQL
# =============================================================================
log_info "Paso 4/6: Instalando y configurando PostgreSQL..."
apt-get install -y postgresql postgresql-client
systemctl enable postgresql
systemctl start postgresql

# Crear usuario de PostgreSQL para Odoo (si no existe)
if su - postgres -c "psql -tAc \"SELECT 1 FROM pg_roles WHERE rolname='${ODOO_USER}'\"" | grep -q 1; then
    log_warn "El usuario de PostgreSQL '${ODOO_USER}' ya existe, omitiendo creación."
else
    su - postgres -c "createuser -s ${ODOO_USER}"
    log_info "Usuario de PostgreSQL '${ODOO_USER}' creado correctamente."
fi

# =============================================================================
# PASO 5: Crear usuario del sistema, clonar repositorio y configurar
# =============================================================================
log_info "Paso 5/6: Configurando usuario del sistema y clonando el repositorio..."

# Crear usuario del sistema para Odoo (si no existe)
if id "${ODOO_USER}" &>/dev/null; then
    log_warn "El usuario del sistema '${ODOO_USER}' ya existe, omitiendo creación."
else
    adduser --system --home "${ODOO_HOME}" --group "${ODOO_USER}"
    log_info "Usuario del sistema '${ODOO_USER}' creado correctamente."
fi

# Clonar el repositorio completo de Odoo
if [ -d "${ODOO_DIR}" ]; then
    log_warn "El directorio ${ODOO_DIR} ya existe. Actualizando con git pull..."
    su - "${ODOO_USER}" -s /bin/bash -c "cd ${ODOO_DIR} && git pull"
else
    git clone --depth 1 --branch "${ODOO_BRANCH}" "${ODOO_REPO}" "${ODOO_DIR}"
    log_info "Repositorio de Odoo clonado correctamente en ${ODOO_DIR}."
fi

# Establecer permisos
chown -R "${ODOO_USER}:${ODOO_USER}" "${ODOO_HOME}"

# Crear directorio de logs
mkdir -p "${ODOO_LOG_DIR}"
chown "${ODOO_USER}:${ODOO_USER}" "${ODOO_LOG_DIR}"

# =============================================================================
# PASO 6: Crear archivo de configuración e iniciar Odoo
# =============================================================================
log_info "Paso 6/6: Creando configuración e iniciando Odoo..."

# Crear directorio de configuración
mkdir -p "$(dirname "${ODOO_CONF}")"

# Generar una contraseña maestra aleatoria
ADMIN_PASSWD=$(python3 -c "import secrets; print(secrets.token_urlsafe(16))")

# Crear archivo de configuración
cat > "${ODOO_CONF}" <<EOF
[options]
; Contraseña maestra para operaciones de base de datos (cámbiala si es necesario)
admin_passwd = ${ADMIN_PASSWD}
db_host = False
db_port = False
db_user = ${ODOO_USER}
db_password = False
addons_path = ${ODOO_DIR}/addons
logfile = ${ODOO_LOG_DIR}/odoo-server.log
default_productivity_apps = True

; Optimizaciones para Raspberry Pi 5 (8 GB RAM)
workers = 2
max_cron_threads = 1
limit_memory_hard = 2684354560
limit_memory_soft = 2147483648
limit_time_cpu = 600
limit_time_real = 1200
EOF

chown "${ODOO_USER}:${ODOO_USER}" "${ODOO_CONF}"
chmod 640 "${ODOO_CONF}"

# Crear servicio de systemd
cat > /etc/systemd/system/odoo.service <<EOF
[Unit]
Description=Odoo
After=network.target postgresql.service

[Service]
Type=simple
SyslogIdentifier=odoo
PermissionsStartOnly=true
User=${ODOO_USER}
Group=${ODOO_USER}
ExecStart=${ODOO_DIR}/odoo-bin -c ${ODOO_CONF}
StandardOutput=journal+console

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable odoo
systemctl start odoo

# =============================================================================
# Resumen final
# =============================================================================
echo ""
echo "============================================================================="
log_info "¡Instalación de Odoo completada!"
echo "============================================================================="
echo ""
echo "  Accede a Odoo desde tu navegador:"
IP_ADDR=$(hostname -I | awk '{print $1}')
echo "    http://${IP_ADDR}:8069"
echo ""
echo "  Archivo de configuración: ${ODOO_CONF}"
echo "  Directorio de logs:       ${ODOO_LOG_DIR}/odoo-server.log"
echo "  Directorio de Odoo:       ${ODOO_DIR}"
echo ""
echo "  Comandos útiles:"
echo "    sudo systemctl start odoo     # Iniciar Odoo"
echo "    sudo systemctl stop odoo      # Detener Odoo"
echo "    sudo systemctl restart odoo   # Reiniciar Odoo"
echo "    sudo systemctl status odoo    # Ver estado"
echo "    sudo journalctl -u odoo -f    # Ver logs en tiempo real"
echo ""
echo "  IMPORTANTE: Tu contraseña maestra (admin_passwd) es:"
echo "    ${ADMIN_PASSWD}"
echo "  Guárdala en un lugar seguro. Puedes cambiarla en ${ODOO_CONF}"
echo ""
echo "============================================================================="
