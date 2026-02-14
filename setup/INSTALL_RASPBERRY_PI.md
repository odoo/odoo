# Instalación de Odoo en Raspberry Pi 5 (8 GB RAM) con Ubuntu Server 24.04 LTS

Esta guía documenta todos los comandos útiles para instalar y administrar Odoo
en una Raspberry Pi 5 con 8 GB de RAM ejecutando Ubuntu Server 24.04 LTS.

---

## Requisitos previos

| Componente | Recomendación |
|---|---|
| Hardware | Raspberry Pi 5 – 8 GB RAM |
| Sistema Operativo | Ubuntu Server 24.04 LTS (arm64) |
| Almacenamiento | Tarjeta microSD de 32 GB o superior (se recomienda SSD por USB) |
| Red | Conexión a Internet (Ethernet o Wi-Fi) |

---

## Comandos útiles Pre-Instalación

### 1. Actualizar el sistema operativo

```bash
sudo apt update && sudo apt upgrade -y && sudo apt dist-upgrade -y
sudo reboot
```

### 2. Verificar la versión del sistema

```bash
lsb_release -a
uname -m          # Debe mostrar aarch64
python3 --version # Debe ser 3.12.x en Ubuntu 24.04
```

### 3. Verificar recursos disponibles

```bash
free -h           # Memoria RAM disponible
df -h             # Espacio en disco
nproc             # Número de núcleos de CPU
```

### 4. Configurar la zona horaria y el locale

```bash
sudo timedatectl set-timezone America/Mexico_City   # Ajustar según tu ubicación
sudo dpkg-reconfigure locales                        # Seleccionar es_MX.UTF-8 o es_ES.UTF-8
```

### 5. Instalar paquetes base del sistema

```bash
sudo apt install -y git python3-full python3-pip python3-venv \
    build-essential wget curl libldap2-dev libsasl2-dev \
    libpq-dev libjpeg-dev zlib1g-dev libfreetype6-dev \
    liblcms2-dev libwebp-dev libtiff5-dev libxml2-dev \
    libxslt1-dev libffi-dev nodejs npm
```

### 6. Instalar PostgreSQL

```bash
sudo apt install -y postgresql postgresql-client
sudo systemctl enable postgresql
sudo systemctl start postgresql
```

### 7. Crear usuario de PostgreSQL para Odoo

```bash
sudo su - postgres -c "createuser -s odoo"
```

### 8. Crear usuario del sistema para Odoo (opcional, recomendado en producción)

```bash
sudo adduser --system --home /opt/odoo --group odoo
```

### 9. Instalar wkhtmltopdf (para reportes PDF)

```bash
# Ubuntu 24.04 en arm64
sudo apt install -y wkhtmltopdf
```

### 10. Instalar las dependencias de Python de Odoo (paquetes del sistema)

```bash
sudo apt install -y \
    python3-asn1crypto python3-babel python3-cbor2 python3-chardet \
    python3-cryptography python3-dateutil python3-docutils python3-freezegun \
    python3-geoip2 python3-gevent python3-greenlet python3-idna python3-pil \
    python3-jinja2 python3-libsass python3-lxml python3-lxml-html-clean \
    python3-magic python3-markupsafe python3-num2words python3-ofxparse \
    python3-openpyxl python3-passlib python3-polib python3-psutil \
    python3-psycopg2 python3-openssl python3-pypdf2 python3-rjsmin \
    python3-qrcode python3-renderpm python3-reportlab python3-requests \
    python3-stdnum python3-tz python3-urllib3 python3-vobject python3-werkzeug \
    python3-xlsxwriter python3-xlrd python3-zeep
```

### 11. Instalar fuentes requeridas

```bash
sudo apt install -y fonts-dejavu-core fonts-inconsolata \
    fonts-font-awesome fonts-roboto-unhinted gsfonts
```

---

## Clonar el repositorio e iniciar Odoo

### 12. Clonar el repositorio

```bash
git clone https://github.com/odoo/odoo.git /opt/odoo/odoo
```

### 13. (Opcional) Instalar dependencias de Python con pip en un entorno virtual

Si prefieres usar un entorno virtual en lugar de los paquetes del sistema:

```bash
cd /opt/odoo/odoo
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 14. Iniciar Odoo por primera vez

```bash
cd /opt/odoo/odoo
./odoo-bin --addons-path=addons -d odoo
```

Odoo estará disponible en: `http://<IP_DE_TU_RASPBERRY>:8069`

---

## Comandos útiles Post-Instalación

### Administración del servicio

```bash
# Iniciar Odoo manualmente
cd /opt/odoo/odoo && ./odoo-bin -c /etc/odoo/odoo.conf

# Detener Odoo (si se ejecuta en primer plano)
# Presionar Ctrl+C

# Ver los logs en tiempo real
tail -f /var/log/odoo/odoo-server.log
```

### Crear un archivo de configuración

```bash
sudo mkdir -p /etc/odoo
sudo cp /opt/odoo/odoo/debian/odoo.conf /etc/odoo/odoo.conf
sudo chown odoo:odoo /etc/odoo/odoo.conf
sudo chmod 640 /etc/odoo/odoo.conf

# Editar la configuración
sudo nano /etc/odoo/odoo.conf
```

Parámetros importantes en `odoo.conf`:

> ⚠️ **ADVERTENCIA DE SEGURIDAD:** El parámetro `admin_passwd` es la contraseña
> maestra que otorga acceso completo a la gestión de bases de datos (crear,
> duplicar, eliminar). **Nunca** uses un valor débil como `admin` en producción.
> El script de instalación genera una contraseña aleatoria automáticamente.

```ini
[options]
admin_passwd = TU_CONTRASEÑA_MAESTRA_SEGURA
db_host = False
db_port = False
db_user = odoo
db_password = False
addons_path = /opt/odoo/odoo/addons
logfile = /var/log/odoo/odoo-server.log
default_productivity_apps = True
```

### Crear directorio de logs

```bash
sudo mkdir -p /var/log/odoo
sudo chown odoo:odoo /var/log/odoo
```

### Configurar Odoo como servicio de systemd

```bash
sudo tee /etc/systemd/system/odoo.service > /dev/null <<EOF
[Unit]
Description=Odoo
After=network.target postgresql.service

[Service]
Type=simple
SyslogIdentifier=odoo
PermissionsStartOnly=true
User=odoo
Group=odoo
ExecStart=/opt/odoo/odoo/odoo-bin -c /etc/odoo/odoo.conf
StandardOutput=journal+console

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable odoo
sudo systemctl start odoo
```

### Comandos de administración del servicio

```bash
sudo systemctl start odoo      # Iniciar el servicio
sudo systemctl stop odoo       # Detener el servicio
sudo systemctl restart odoo    # Reiniciar el servicio
sudo systemctl status odoo     # Ver estado del servicio
sudo journalctl -u odoo -f     # Ver logs del servicio en tiempo real
```

### Administración de PostgreSQL

```bash
# Listar bases de datos
sudo su - postgres -c "psql -l"

# Crear una nueva base de datos
sudo su - postgres -c "createdb -O odoo mi_empresa"

# Eliminar una base de datos
sudo su - postgres -c "dropdb mi_empresa"

# Hacer respaldo de una base de datos
sudo su - postgres -c "pg_dump mi_empresa > /tmp/mi_empresa_backup.sql"

# Restaurar un respaldo
sudo su - postgres -c "psql mi_empresa < /tmp/mi_empresa_backup.sql"
```

### Actualizar Odoo

```bash
cd /opt/odoo/odoo
git pull
sudo systemctl restart odoo
```

### Actualizar un módulo específico

```bash
cd /opt/odoo/odoo
./odoo-bin -c /etc/odoo/odoo.conf -d mi_empresa -u nombre_del_modulo --stop-after-init
```

### Instalar un módulo nuevo

```bash
cd /opt/odoo/odoo
./odoo-bin -c /etc/odoo/odoo.conf -d mi_empresa -i nombre_del_modulo --stop-after-init
```

### Verificar el estado general del sistema

```bash
# Memoria y CPU
htop

# Espacio en disco
df -h

# Conexiones activas a PostgreSQL
sudo su - postgres -c "psql -c 'SELECT * FROM pg_stat_activity;'"

# Puertos en uso
sudo ss -tlnp | grep -E '(8069|5432)'
```

### Optimizaciones recomendadas para Raspberry Pi 5

```bash
# Ajustar workers según los recursos disponibles (para 8 GB RAM)
# Agregar al archivo /etc/odoo/odoo.conf:
#   workers = 2
#   max_cron_threads = 1
#   limit_memory_hard = 2684354560
#   limit_memory_soft = 2147483648
#   limit_time_cpu = 600
#   limit_time_real = 1200
```

---

## Script de instalación automatizada

Para una instalación automatizada, consulta el script `install_odoo_rpi5.sh`
incluido en este mismo directorio:

```bash
chmod +x setup/install_odoo_rpi5.sh
sudo bash setup/install_odoo_rpi5.sh
```
