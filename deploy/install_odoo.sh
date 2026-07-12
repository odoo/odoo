#!/bin/bash
# =============================================================================
# Instalação automática do Odoo 19 — Oracle Linux 9 ARM (VM.Standard.A1.Flex)
# Repositório: https://github.com/cristoffer4-arch/odoo-19
# =============================================================================
set -euo pipefail

# ── Variáveis ─────────────────────────────────────────────────────────────────
DB_USER="odoo"
DB_PASS="Alex2201@"
DB_NAME="odoo_prod"
ODOO_USER="odoo"
ODOO_HOME="/opt/odoo"
ODOO_REPO="https://github.com/cristoffer4-arch/odoo-19.git"
ODOO_BRANCH="main"          # branch principal do repo
ODOO_PORT="8069"
PYTHON="python3.11"

# IP público detectado automaticamente (usado para o domínio nip.io)
PUBLIC_IP=$(curl -s --max-time 10 ifconfig.me || curl -s --max-time 10 api.ipify.org)
DOMAIN="${PUBLIC_IP}.nip.io"

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║        Instalação Odoo 19 — Oracle Linux 9 ARM              ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "  IP público  : ${PUBLIC_IP}"
echo "  Domínio     : ${DOMAIN}"
echo "  Banco       : ${DB_NAME}"
echo "  Porta Odoo  : ${ODOO_PORT}"
echo ""
read -rp "  Continuar? (Enter para sim / Ctrl+C para cancelar): "

# =============================================================================
# 1. SISTEMA BASE
# =============================================================================
echo ""
echo "▶ [1/9] Atualizando sistema e instalando dependências..."

dnf update -y -q
dnf install -y -q \
    epel-release oracle-epel-release-el9 2>/dev/null || dnf install -y -q epel-release

dnf install -y -q \
    git curl wget vim \
    python3.11 python3.11-devel python3.11-pip \
    gcc gcc-c++ make \
    libxml2-devel libxslt-devel \
    libjpeg-turbo-devel libpng-devel freetype-devel \
    openldap-devel \
    nodejs npm \
    fontconfig \
    libffi-devel \
    openssl-devel \
    bzip2-devel \
    xz-devel \
    readline-devel \
    zlib-devel

echo "  ✓ Dependências do sistema instaladas"

# =============================================================================
# 2. POSTGRESQL 15
# =============================================================================
echo ""
echo "▶ [2/9] Instalando PostgreSQL 15..."

# Repo oficial do PostgreSQL para OL9
dnf install -y -q https://download.postgresql.org/pub/repos/yum/reporpms/EL-9-aarch64/pgdg-redhat-repo-latest.noarch.rpm 2>/dev/null || true
dnf -qy module disable postgresql 2>/dev/null || true
dnf install -y -q postgresql15-server postgresql15-contrib

# Inicializa o cluster
/usr/pgsql-15/bin/postgresql-15-setup initdb

# Configura autenticação local (md5 para odoo, trust para postgres local)
PG_HBA="/var/lib/pgsql/15/data/pg_hba.conf"
cat > "$PG_HBA" <<'PGHBA'
local   all             postgres                                peer
local   all             all                                     md5
host    all             all             127.0.0.1/32            md5
host    all             all             ::1/128                 md5
PGHBA

systemctl enable postgresql-15 --now

# Cria usuário e banco
sudo -u postgres psql -c "CREATE USER ${DB_USER} WITH PASSWORD '${DB_PASS}' CREATEDB;" 2>/dev/null || \
    sudo -u postgres psql -c "ALTER USER ${DB_USER} WITH PASSWORD '${DB_PASS}';"
sudo -u postgres psql -c "CREATE DATABASE ${DB_NAME} OWNER ${DB_USER};" 2>/dev/null || true

export PATH="/usr/pgsql-15/bin:$PATH"
echo 'export PATH="/usr/pgsql-15/bin:$PATH"' >> /etc/profile.d/pgsql.sh

echo "  ✓ PostgreSQL 15 instalado e configurado"

# =============================================================================
# 3. WKHTMLTOPDF (ARM build para RHEL/OL 9)
# =============================================================================
echo ""
echo "▶ [3/9] Instalando wkhtmltopdf (ARM64)..."

WKHTMLTOPDF_URL="https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6.1-2/wkhtmltox-0.12.6.1-2.almalinux9.aarch64.rpm"
WKHTMLTOPDF_RPM="/tmp/wkhtmltox.rpm"

wget -q -O "$WKHTMLTOPDF_RPM" "$WKHTMLTOPDF_URL"
dnf install -y -q "$WKHTMLTOPDF_RPM"
rm -f "$WKHTMLTOPDF_RPM"

echo "  ✓ wkhtmltopdf $(wkhtmltopdf --version 2>&1 | head -1)"

# =============================================================================
# 4. USUÁRIO ODOO
# =============================================================================
echo ""
echo "▶ [4/9] Criando usuário do sistema 'odoo'..."

useradd -m -d "$ODOO_HOME" -s /bin/bash "$ODOO_USER" 2>/dev/null || echo "  (usuário já existe)"
mkdir -p "$ODOO_HOME"/{logs,data,config}
chown -R "$ODOO_USER":"$ODOO_USER" "$ODOO_HOME"

echo "  ✓ Usuário '${ODOO_USER}' configurado"

# =============================================================================
# 5. CLONE DO REPOSITÓRIO
# =============================================================================
echo ""
echo "▶ [5/9] Clonando repositório..."

# Se o repo for privado, o git pedirá credenciais.
# Para automatizar, adicione um deploy token assim:
#   git clone https://<TOKEN>@github.com/cristoffer4-arch/odoo-19.git
sudo -u "$ODOO_USER" git clone \
    --branch "$ODOO_BRANCH" \
    --depth 1 \
    "$ODOO_REPO" \
    "${ODOO_HOME}/server"

echo "  ✓ Repositório clonado em ${ODOO_HOME}/server"

# =============================================================================
# 6. AMBIENTE PYTHON (venv + dependências)
# =============================================================================
echo ""
echo "▶ [6/9] Criando ambiente Python e instalando dependências..."

sudo -u "$ODOO_USER" $PYTHON -m venv "${ODOO_HOME}/venv"
VENV_PIP="${ODOO_HOME}/venv/bin/pip"

sudo -u "$ODOO_USER" $VENV_PIP install --upgrade pip wheel setuptools -q

# Dependências do Odoo 19
sudo -u "$ODOO_USER" $VENV_PIP install \
    -r "${ODOO_HOME}/server/requirements.txt" \
    -q 2>&1 | tail -5

echo "  ✓ Ambiente Python configurado"

# =============================================================================
# 7. CONFIGURAÇÃO DO ODOO
# =============================================================================
echo ""
echo "▶ [7/9] Gerando odoo.conf..."

ADMIN_PASSWD=$(python3 -c "import secrets; print(secrets.token_urlsafe(24))")

cat > "${ODOO_HOME}/config/odoo.conf" <<CONF
[options]
; === Servidor ===
http_port = ${ODOO_PORT}
longpolling_port = 8072
proxy_mode = True

; === Banco de dados ===
db_host = 127.0.0.1
db_port = 5432
db_user = ${DB_USER}
db_password = ${DB_PASS}
db_name = ${DB_NAME}

; === Segurança ===
admin_passwd = ${ADMIN_PASSWD}

; === Ficheiros ===
data_dir = ${ODOO_HOME}/data
logfile = ${ODOO_HOME}/logs/odoo.log
log_level = info

; === Performance ===
workers = 2
max_cron_threads = 1
limit_memory_hard = 2684354560
limit_memory_soft = 2147483648
limit_request = 8192
limit_time_cpu = 120
limit_time_real = 240

; === Módulos adicionais ===
addons_path = ${ODOO_HOME}/server/addons,${ODOO_HOME}/server/odoo/addons
CONF

chown "$ODOO_USER":"$ODOO_USER" "${ODOO_HOME}/config/odoo.conf"
chmod 640 "${ODOO_HOME}/config/odoo.conf"

echo "  ✓ odoo.conf criado"
echo "  ⚠  Senha master do Odoo: ${ADMIN_PASSWD}"
echo "     (guarde em local seguro!)"

# =============================================================================
# 8. SERVIÇO SYSTEMD
# =============================================================================
echo ""
echo "▶ [8/9] Configurando serviço systemd..."

cat > /etc/systemd/system/odoo.service <<SERVICE
[Unit]
Description=Odoo 19
Requires=postgresql-15.service
After=network.target postgresql-15.service

[Service]
Type=simple
User=${ODOO_USER}
Group=${ODOO_USER}
ExecStart=${ODOO_HOME}/venv/bin/python3 ${ODOO_HOME}/server/odoo-bin \
    --config ${ODOO_HOME}/config/odoo.conf
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=odoo

[Install]
WantedBy=multi-user.target
SERVICE

systemctl daemon-reload
systemctl enable odoo
systemctl start odoo

echo "  ✓ Serviço odoo ativo"

# =============================================================================
# 9. NGINX + CERTBOT (SSL via nip.io)
# =============================================================================
echo ""
echo "▶ [9/9] Instalando Nginx e SSL (Let's Encrypt)..."

dnf install -y -q nginx certbot python3-certbot-nginx

# Config Nginx (HTTP primeiro, depois Certbot adiciona HTTPS)
cat > /etc/nginx/conf.d/odoo.conf <<NGINX
upstream odoo {
    server 127.0.0.1:${ODOO_PORT};
}
upstream odoo_chat {
    server 127.0.0.1:8072;
}

server {
    listen 80;
    server_name ${DOMAIN};

    # Certbot challenge
    location /.well-known/acme-challenge/ { root /var/www/html; }

    # Tamanho máximo de upload
    client_max_body_size 128m;

    # Compressão
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml;

    # Proxy para Odoo
    location / {
        proxy_pass http://odoo;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_redirect off;
        proxy_read_timeout 720s;
        proxy_connect_timeout 720s;
        proxy_send_timeout 720s;
    }

    # Longpolling (chat, notificações)
    location /websocket {
        proxy_pass http://odoo_chat;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    # Cache de assets estáticos
    location ~* /web/static/ {
        proxy_pass http://odoo;
        proxy_cache_valid 200 90d;
        proxy_buffering on;
        expires 864000;
        add_header Cache-Control "public, immutable";
    }
}
NGINX

nginx -t
systemctl enable nginx --now

# SSL com Certbot
mkdir -p /var/www/html
certbot --nginx \
    -d "$DOMAIN" \
    --non-interactive \
    --agree-tos \
    -m "admin@${DOMAIN}" \
    --redirect

# Renovação automática
echo "0 3 * * * root certbot renew --quiet" > /etc/cron.d/certbot-renew

echo "  ✓ Nginx com SSL configurado"

# =============================================================================
# FIREWALL
# =============================================================================
echo ""
echo "▶ Configurando firewall (firewalld)..."

systemctl enable firewalld --now
firewall-cmd --permanent --add-service=http
firewall-cmd --permanent --add-service=https
firewall-cmd --permanent --add-service=ssh
firewall-cmd --reload

echo "  ✓ Firewall configurado"

# =============================================================================
# RESUMO FINAL
# =============================================================================
echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                  ✅  INSTALAÇÃO CONCLUÍDA                   ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "  🌐 URL          : https://${DOMAIN}"
echo "  👤 Login Odoo   : admin"
echo "  🔑 Senha master : ${ADMIN_PASSWD}"
echo "  🗄  Banco        : ${DB_NAME} (usuário: ${DB_USER})"
echo ""
echo "  Logs do Odoo   : journalctl -u odoo -f"
echo "  Reiniciar      : systemctl restart odoo"
echo "  Status         : systemctl status odoo"
echo ""
echo "  ⚠  IMPORTANTE: Anote a senha master acima!"
echo ""
