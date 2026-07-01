# Prompt de Automação — Odoo 19 no Oracle OCI
# Para usar no Comet Pro (ou qualquer agente de automação com acesso SSH)

---

## CONTEXTO

Você é um agente de automação. Sua tarefa é instalar e configurar completamente
o Odoo 19 em um servidor Oracle OCI com Oracle Linux 9 ARM (VM.Standard.A1.Flex).
Execute cada passo em ordem, verifique o sucesso antes de avançar, e reporte
o resultado final com a URL de acesso.

---

## VARIÁVEIS DE AMBIENTE

```
SERVIDOR_IP      = <IP_PÚBLICO_DA_INSTÂNCIA_OCI>
SSH_USER         = opc
DB_USER          = odoo
DB_PASS          = Alex2201@
DB_NAME          = odoo_prod
ODOO_PORT        = 8069
ODOO_HOME        = /opt/odoo
ODOO_USER        = odoo
REPO_URL         = https://github.com/cristoffer4-arch/odoo-19.git
REPO_BRANCH      = main
PYTHON           = python3.11
```

---

## PASSO 1 — CONECTAR AO SERVIDOR

```bash
ssh -o StrictHostKeyChecking=no opc@${SERVIDOR_IP}
sudo -i
```

Verificar: `whoami` deve retornar `root`.

---

## PASSO 2 — ATUALIZAR SISTEMA E INSTALAR DEPENDÊNCIAS

```bash
dnf update -y -q

dnf install -y -q epel-release

dnf install -y -q \
    git curl wget vim \
    python3.11 python3.11-devel python3.11-pip \
    gcc gcc-c++ make \
    libxml2-devel libxslt-devel \
    libjpeg-turbo-devel libpng-devel freetype-devel \
    openldap-devel nodejs npm fontconfig \
    libffi-devel openssl-devel bzip2-devel \
    xz-devel readline-devel zlib-devel
```

Verificar: `python3.11 --version` deve retornar `Python 3.11.x`

---

## PASSO 3 — INSTALAR POSTGRESQL 15

```bash
dnf install -y -q \
    https://download.postgresql.org/pub/repos/yum/reporpms/EL-9-aarch64/pgdg-redhat-repo-latest.noarch.rpm

dnf -qy module disable postgresql

dnf install -y -q postgresql15-server postgresql15-contrib

/usr/pgsql-15/bin/postgresql-15-setup initdb

cat > /var/lib/pgsql/15/data/pg_hba.conf <<'PGHBA'
local   all             postgres                                peer
local   all             all                                     md5
host    all             all             127.0.0.1/32            md5
host    all             all             ::1/128                 md5
PGHBA

systemctl enable postgresql-15 --now

echo 'export PATH="/usr/pgsql-15/bin:$PATH"' >> /etc/profile.d/pgsql.sh
export PATH="/usr/pgsql-15/bin:$PATH"

sudo -u postgres psql -c "CREATE USER odoo WITH PASSWORD 'Alex2201@' CREATEDB;" 2>/dev/null || \
    sudo -u postgres psql -c "ALTER USER odoo WITH PASSWORD 'Alex2201@';"

sudo -u postgres psql -c "CREATE DATABASE odoo_prod OWNER odoo;" 2>/dev/null || true
```

Verificar: `sudo -u postgres psql -c "\du"` deve mostrar o usuário `odoo`.

---

## PASSO 4 — INSTALAR WKHTMLTOPDF (ARM64 para Oracle Linux 9)

```bash
wget -q -O /tmp/wkhtmltox.rpm \
    https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6.1-2/wkhtmltox-0.12.6.1-2.almalinux9.aarch64.rpm

dnf install -y -q /tmp/wkhtmltox.rpm
rm -f /tmp/wkhtmltox.rpm
```

Verificar: `wkhtmltopdf --version` deve retornar `wkhtmltopdf 0.12.6.1`

---

## PASSO 5 — CRIAR USUÁRIO DO SISTEMA ODOO

```bash
useradd -m -d /opt/odoo -s /bin/bash odoo 2>/dev/null || true

mkdir -p /opt/odoo/{logs,data,config,backups}
chown -R odoo:odoo /opt/odoo
```

Verificar: `id odoo` deve mostrar o usuário.

---

## PASSO 6 — CLONAR REPOSITÓRIO

```bash
sudo -u odoo git clone \
    --branch main \
    --depth 1 \
    https://github.com/cristoffer4-arch/odoo-19.git \
    /opt/odoo/server
```

Se o repositório for privado, usar token:
```bash
sudo -u odoo git clone \
    --branch main \
    --depth 1 \
    https://<GITHUB_TOKEN>@github.com/cristoffer4-arch/odoo-19.git \
    /opt/odoo/server
```

Verificar: `ls /opt/odoo/server/odoo-bin` deve existir.

---

## PASSO 7 — AMBIENTE PYTHON E DEPENDÊNCIAS

```bash
sudo -u odoo python3.11 -m venv /opt/odoo/venv

sudo -u odoo /opt/odoo/venv/bin/pip install --upgrade pip wheel setuptools -q

sudo -u odoo /opt/odoo/venv/bin/pip install \
    -r /opt/odoo/server/requirements.txt -q
```

Verificar: `/opt/odoo/venv/bin/python3 -c "import odoo; print('OK')"` (dentro do server dir)

---

## PASSO 8 — GERAR SENHA MASTER E CRIAR ODOO.CONF

```bash
ADMIN_PASSWD=$(python3 -c "import secrets; print(secrets.token_urlsafe(24))")
echo "SENHA MASTER ODOO: ${ADMIN_PASSWD}"
echo ">>> GUARDE ESTA SENHA! <<<"

cat > /opt/odoo/config/odoo.conf <<CONF
[options]
http_port = 8069
longpolling_port = 8072
proxy_mode = True

db_host = 127.0.0.1
db_port = 5432
db_user = odoo
db_password = Alex2201@
db_name = odoo_prod

admin_passwd = ${ADMIN_PASSWD}

data_dir = /opt/odoo/data
logfile = /opt/odoo/logs/odoo.log
log_level = info

workers = 2
max_cron_threads = 1
limit_memory_hard = 2684354560
limit_memory_soft = 2147483648
limit_request = 8192
limit_time_cpu = 120
limit_time_real = 240

addons_path = /opt/odoo/server/addons,/opt/odoo/server/odoo/addons
CONF

chown odoo:odoo /opt/odoo/config/odoo.conf
chmod 640 /opt/odoo/config/odoo.conf
```

---

## PASSO 9 — SERVIÇO SYSTEMD

```bash
cat > /etc/systemd/system/odoo.service <<'SERVICE'
[Unit]
Description=Odoo 19
Requires=postgresql-15.service
After=network.target postgresql-15.service

[Service]
Type=simple
User=odoo
Group=odoo
ExecStart=/opt/odoo/venv/bin/python3 /opt/odoo/server/odoo-bin \
    --config /opt/odoo/config/odoo.conf
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
```

Verificar: `systemctl status odoo` deve mostrar `active (running)`.
Aguardar 10 segundos e verificar logs: `journalctl -u odoo -n 20`

---

## PASSO 10 — INSTALAR NGINX

```bash
dnf install -y -q nginx
```

---

## PASSO 11 — DETECTAR IP E CONFIGURAR NGINX COM NIP.IO

```bash
PUBLIC_IP=$(curl -s --max-time 10 ifconfig.me)
DOMAIN="${PUBLIC_IP}.nip.io"
echo "DOMÍNIO: https://${DOMAIN}"

cat > /etc/nginx/conf.d/odoo.conf <<NGINX
upstream odoo_backend {
    server 127.0.0.1:8069;
}
upstream odoo_chat {
    server 127.0.0.1:8072;
}

server {
    listen 80;
    server_name ${DOMAIN};

    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }

    client_max_body_size 128m;

    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml;

    location / {
        proxy_pass http://odoo_backend;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_redirect off;
        proxy_read_timeout 720s;
        proxy_connect_timeout 720s;
        proxy_send_timeout 720s;
    }

    location /websocket {
        proxy_pass http://odoo_chat;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location ~* /web/static/ {
        proxy_pass http://odoo_backend;
        expires 864000;
        add_header Cache-Control "public, immutable";
    }
}
NGINX

mkdir -p /var/www/html
nginx -t
systemctl enable nginx --now
```

Verificar: `curl -s -o /dev/null -w "%{http_code}" http://${DOMAIN}` deve retornar `200` ou `303`.

---

## PASSO 12 — SSL COM LET'S ENCRYPT (CERTBOT)

```bash
dnf install -y -q certbot python3-certbot-nginx

certbot --nginx \
    -d "${DOMAIN}" \
    --non-interactive \
    --agree-tos \
    -m "admin@${DOMAIN}" \
    --redirect

echo "0 3 * * * root certbot renew --quiet --post-hook 'systemctl reload nginx'" \
    > /etc/cron.d/certbot-renew
```

Verificar: `curl -s -o /dev/null -w "%{http_code}" https://${DOMAIN}` deve retornar `200`.

---

## PASSO 13 — FIREWALL

```bash
systemctl enable firewalld --now

firewall-cmd --permanent --add-service=http
firewall-cmd --permanent --add-service=https
firewall-cmd --permanent --add-service=ssh
firewall-cmd --reload

firewall-cmd --list-all
```

---

## PASSO 14 — BACKUP AUTOMÁTICO DIÁRIO

```bash
cat > /opt/odoo/backup_odoo.sh <<'BACKUP'
#!/bin/bash
set -euo pipefail
export PATH="/usr/pgsql-15/bin:$PATH"
export PGPASSWORD="Alex2201@"

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/opt/odoo/backups"
mkdir -p "$BACKUP_DIR"

pg_dump -U odoo -h 127.0.0.1 odoo_prod | gzip > "${BACKUP_DIR}/db_${DATE}.sql.gz"

if [ -d "/opt/odoo/data/filestore/odoo_prod" ]; then
    tar -czf "${BACKUP_DIR}/filestore_${DATE}.tar.gz" \
        -C /opt/odoo/data/filestore odoo_prod
fi

find "$BACKUP_DIR" -name "*.gz" -mtime +14 -delete
echo "[$(date)] Backup: db_${DATE}.sql.gz"
BACKUP

chmod +x /opt/odoo/backup_odoo.sh
chown odoo:odoo /opt/odoo/backup_odoo.sh

echo "0 2 * * * root bash /opt/odoo/backup_odoo.sh >> /opt/odoo/logs/backup.log 2>&1" \
    > /etc/cron.d/odoo-backup
```

Verificar: `bash /opt/odoo/backup_odoo.sh` deve criar o arquivo sem erros.

---

## PASSO 15 — INICIALIZAR BANCO DO ODOO

```bash
systemctl stop odoo

sudo -u odoo /opt/odoo/venv/bin/python3 /opt/odoo/server/odoo-bin \
    --config /opt/odoo/config/odoo.conf \
    --init base \
    --stop-after-init \
    --log-level=warn

systemctl start odoo
```

Aguardar 15 segundos após reiniciar.

---

## PASSO 16 — INSTALAR MÓDULOS CUSTOMIZADOS

```bash
systemctl stop odoo

sudo -u odoo /opt/odoo/venv/bin/python3 /opt/odoo/server/odoo-bin \
    --config /opt/odoo/config/odoo.conf \
    --init theme_b24ui,hr_maestro_integration,project_maestro_timer,payment_maestro_setup \
    --stop-after-init \
    --log-level=warn

systemctl start odoo
```

Verificar: `journalctl -u odoo -n 30` não deve conter `ERROR` ou `CRITICAL`.

---

## PASSO 17 — VERIFICAÇÃO FINAL

```bash
PUBLIC_IP=$(curl -s ifconfig.me)
DOMAIN="${PUBLIC_IP}.nip.io"

echo ""
echo "=========================================="
echo "  VERIFICAÇÃO FINAL"
echo "=========================================="
echo ""

# PostgreSQL
sudo -u postgres psql -c "\l" | grep odoo_prod && echo "✅ Banco OK" || echo "❌ Banco FALHOU"

# Odoo service
systemctl is-active odoo && echo "✅ Odoo service OK" || echo "❌ Odoo service FALHOU"

# Nginx
systemctl is-active nginx && echo "✅ Nginx OK" || echo "❌ Nginx FALHOU"

# HTTP response
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "https://${DOMAIN}" 2>/dev/null || echo "000")
[ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "303" ] \
    && echo "✅ Site respondendo (HTTP ${HTTP_CODE})" \
    || echo "❌ Site não responde (HTTP ${HTTP_CODE})"

# Espaço em disco
df -h / | tail -1

echo ""
echo "=========================================="
echo "  ACESSO AO SISTEMA"
echo "=========================================="
echo ""
echo "  🌐 URL      : https://${DOMAIN}"
echo "  👤 Login    : admin"
echo "  🔑 Senha BD : Alex2201@"
echo ""
echo "  Logs        : journalctl -u odoo -f"
echo "  Reiniciar   : systemctl restart odoo"
echo "  Backup      : bash /opt/odoo/backup_odoo.sh"
echo ""
```

---

## TRATAMENTO DE ERROS

Se qualquer passo falhar:

```bash
# Ver logs do Odoo
journalctl -u odoo -n 50 --no-pager

# Ver logs do Nginx
journalctl -u nginx -n 20 --no-pager

# Testar configuração do Nginx
nginx -t

# Testar conexão com banco
PGPASSWORD="Alex2201@" psql -U odoo -h 127.0.0.1 -d odoo_prod -c "SELECT 1;"

# Reiniciar tudo
systemctl restart postgresql-15 odoo nginx
```

---

## RESULTADO ESPERADO

Ao final de todos os passos, o agente deve reportar:

```
✅ Instalação concluída com sucesso
URL: https://<IP>.nip.io
Todos os serviços ativos: PostgreSQL, Odoo, Nginx
SSL: Let's Encrypt válido
Módulos instalados: theme_b24ui, hr_maestro_integration,
                    project_maestro_timer, payment_maestro_setup
Backup automático: diário às 02h00
```
