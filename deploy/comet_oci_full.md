# Prompt de Automação Completo — OCI + Odoo 19
# Do zero: criação da instância até o sistema funcionando
# Para Comet Pro com acesso à OCI CLI e SSH

---

## OBJETIVO

Você é um agente de automação. Execute todos os passos abaixo em sequência
para criar uma instância Oracle OCI do zero e instalar o Odoo 19 completo.
Verifique o sucesso de cada passo antes de avançar.
Ao final, reporte a URL de acesso, senha master e status de todos os serviços.

---

## CREDENCIAIS NECESSÁRIAS (preencher antes de iniciar)

```
OCI_TENANCY_OCID     = ocid1.tenancy.oc1..xxxxxxxx        # Perfil → Tenancy
OCI_USER_OCID        = ocid1.user.oc1..xxxxxxxx            # Perfil → Usuário
OCI_FINGERPRINT      = xx:xx:xx:xx:xx:xx:xx:xx             # API Key fingerprint
OCI_KEY_PATH         = ~/.oci/oci_api_key.pem              # Chave privada OCI
OCI_REGION           = sa-saopaulo-1                        # Região São Paulo
OCI_COMPARTMENT_OCID = ocid1.compartment.oc1..xxxxxxxx     # Compartimento raiz

DB_PASS              = Alex2201@
GITHUB_REPO          = https://github.com/cristoffer4-arch/odoo-19.git
GITHUB_BRANCH        = main
```

---

## FASE 1 — CONFIGURAR OCI CLI

### 1.1 Verificar se OCI CLI está instalado

```bash
oci --version
```

Se não estiver instalado:

```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/oracle/oci-cli/master/scripts/install/install.sh)" \
    -- --accept-all-defaults
source ~/.bashrc
```

### 1.2 Configurar autenticação

```bash
mkdir -p ~/.oci

cat > ~/.oci/config <<OCI_CONFIG
[DEFAULT]
user=${OCI_USER_OCID}
fingerprint=${OCI_FINGERPRINT}
key_file=${OCI_KEY_PATH}
tenancy=${OCI_TENANCY_OCID}
region=${OCI_REGION}
OCI_CONFIG

chmod 600 ~/.oci/config
```

### 1.3 Gerar par de chaves SSH para a instância

```bash
ssh-keygen -t ed25519 -f ~/.ssh/odoo_oci -N "" -C "odoo-oci-deploy"
SSH_PUBLIC_KEY=$(cat ~/.ssh/odoo_oci.pub)
echo "Chave SSH pública gerada: ${SSH_PUBLIC_KEY}"
```

### 1.4 Testar conexão com OCI

```bash
oci iam region list --output table
```

Verificar: deve listar as regiões. Se falhar, revisar as credenciais.

---

## FASE 2 — CRIAR INFRAESTRUTURA DE REDE (VCN)

### 2.1 Criar VCN

```bash
VCN_ID=$(oci network vcn create \
    --compartment-id "${OCI_COMPARTMENT_OCID}" \
    --display-name "vcn-odoo-prod" \
    --cidr-block "10.0.0.0/16" \
    --dns-label "odoo" \
    --wait-for-state AVAILABLE \
    --query 'data.id' \
    --raw-output)

echo "VCN criada: ${VCN_ID}"
```

### 2.2 Criar Internet Gateway

```bash
IGW_ID=$(oci network internet-gateway create \
    --compartment-id "${OCI_COMPARTMENT_OCID}" \
    --vcn-id "${VCN_ID}" \
    --display-name "igw-odoo" \
    --is-enabled true \
    --wait-for-state AVAILABLE \
    --query 'data.id' \
    --raw-output)

echo "Internet Gateway: ${IGW_ID}"
```

### 2.3 Configurar Route Table (rota padrão via Internet Gateway)

```bash
RT_ID=$(oci network route-table list \
    --compartment-id "${OCI_COMPARTMENT_OCID}" \
    --vcn-id "${VCN_ID}" \
    --query 'data[0].id' \
    --raw-output)

oci network route-table update \
    --rt-id "${RT_ID}" \
    --route-rules "[{\"cidrBlock\":\"0.0.0.0/0\",\"networkEntityId\":\"${IGW_ID}\"}]" \
    --force

echo "Route Table configurada: ${RT_ID}"
```

### 2.4 Configurar Security List (abrir portas 22, 80, 443)

```bash
SL_ID=$(oci network security-list list \
    --compartment-id "${OCI_COMPARTMENT_OCID}" \
    --vcn-id "${VCN_ID}" \
    --query 'data[0].id' \
    --raw-output)

oci network security-list update \
    --security-list-id "${SL_ID}" \
    --ingress-security-rules '[
        {
            "protocol": "6",
            "source": "0.0.0.0/0",
            "tcpOptions": {"destinationPortRange": {"min": 22, "max": 22}},
            "isStateless": false,
            "description": "SSH"
        },
        {
            "protocol": "6",
            "source": "0.0.0.0/0",
            "tcpOptions": {"destinationPortRange": {"min": 80, "max": 80}},
            "isStateless": false,
            "description": "HTTP"
        },
        {
            "protocol": "6",
            "source": "0.0.0.0/0",
            "tcpOptions": {"destinationPortRange": {"min": 443, "max": 443}},
            "isStateless": false,
            "description": "HTTPS"
        }
    ]' \
    --force

echo "Security List configurada: ${SL_ID}"
```

### 2.5 Criar Subnet pública

```bash
SUBNET_ID=$(oci network subnet create \
    --compartment-id "${OCI_COMPARTMENT_OCID}" \
    --vcn-id "${VCN_ID}" \
    --display-name "subnet-odoo-pub" \
    --cidr-block "10.0.1.0/24" \
    --dns-label "odoo" \
    --route-table-id "${RT_ID}" \
    --security-list-ids "[\"${SL_ID}\"]" \
    --prohibit-public-ip-on-vnic false \
    --wait-for-state AVAILABLE \
    --query 'data.id' \
    --raw-output)

echo "Subnet criada: ${SUBNET_ID}"
```

---

## FASE 3 — CRIAR INSTÂNCIA COMPUTE

### 3.1 Buscar OCID da imagem Oracle Linux 9 ARM mais recente

```bash
IMAGE_OCID=$(oci compute image list \
    --compartment-id "${OCI_COMPARTMENT_OCID}" \
    --operating-system "Oracle Linux" \
    --operating-system-version "9" \
    --shape "VM.Standard.A1.Flex" \
    --sort-by TIMECREATED \
    --sort-order DESC \
    --query 'data[0].id' \
    --raw-output)

echo "Imagem Oracle Linux 9 ARM: ${IMAGE_OCID}"
```

### 3.2 Criar a instância VM.Standard.A1.Flex (Always Free)

```bash
INSTANCE_ID=$(oci compute instance launch \
    --compartment-id "${OCI_COMPARTMENT_OCID}" \
    --display-name "odoo-prod" \
    --image-id "${IMAGE_OCID}" \
    --shape "VM.Standard.A1.Flex" \
    --shape-config '{"ocpus": 4, "memoryInGBs": 24}' \
    --subnet-id "${SUBNET_ID}" \
    --assign-public-ip true \
    --ssh-authorized-keys-file ~/.ssh/odoo_oci.pub \
    --metadata '{"user_data": ""}' \
    --boot-volume-size-in-gbs 100 \
    --wait-for-state RUNNING \
    --query 'data.id' \
    --raw-output)

echo "Instância criada: ${INSTANCE_ID}"
```

Aguardar ~3 minutos para a instância ficar pronta.

### 3.3 Obter o IP público

```bash
PUBLIC_IP=$(oci compute instance list-vnics \
    --instance-id "${INSTANCE_ID}" \
    --query 'data[0]."public-ip"' \
    --raw-output)

DOMAIN="${PUBLIC_IP}.nip.io"
echo "IP Público : ${PUBLIC_IP}"
echo "Domínio    : ${DOMAIN}"
echo "URL final  : https://${DOMAIN}"
```

### 3.4 Aguardar SSH ficar disponível

```bash
echo "Aguardando SSH ficar disponível..."
for i in $(seq 1 30); do
    if ssh -o StrictHostKeyChecking=no \
           -o ConnectTimeout=5 \
           -o BatchMode=yes \
           -i ~/.ssh/odoo_oci \
           opc@${PUBLIC_IP} "echo ok" 2>/dev/null; then
        echo "SSH disponível!"
        break
    fi
    echo "  tentativa ${i}/30... aguardando 10s"
    sleep 10
done
```

---

## FASE 4 — INSTALAR ODOO 19 NO SERVIDOR

A partir daqui, todos os comandos são executados via SSH no servidor.

### 4.1 Copiar script de instalação para o servidor

```bash
scp -i ~/.ssh/odoo_oci -o StrictHostKeyChecking=no \
    /dev/stdin opc@${PUBLIC_IP}:/tmp/install_odoo.sh <<'SCRIPT_EOF'
#!/bin/bash
set -euo pipefail

DB_PASS="Alex2201@"
ODOO_HOME="/opt/odoo"
REPO_URL="https://github.com/cristoffer4-arch/odoo-19.git"
REPO_BRANCH="main"
PUBLIC_IP=$(curl -s --max-time 10 ifconfig.me)
DOMAIN="${PUBLIC_IP}.nip.io"

log() { echo "[$(date +%H:%M:%S)] $*"; }

# ── Passo 1: Sistema e dependências ──────────────────────────────────────────
log "Atualizando sistema..."
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
log "✓ Dependências instaladas"

# ── Passo 2: PostgreSQL 15 ───────────────────────────────────────────────────
log "Instalando PostgreSQL 15..."
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
export PATH="/usr/pgsql-15/bin:$PATH"
echo 'export PATH="/usr/pgsql-15/bin:$PATH"' >> /etc/profile.d/pgsql.sh

sudo -u postgres psql -c "CREATE USER odoo WITH PASSWORD '${DB_PASS}' CREATEDB;" 2>/dev/null || \
    sudo -u postgres psql -c "ALTER USER odoo WITH PASSWORD '${DB_PASS}';"
sudo -u postgres psql -c "CREATE DATABASE odoo_prod OWNER odoo;" 2>/dev/null || true
log "✓ PostgreSQL 15 configurado"

# ── Passo 3: wkhtmltopdf ARM64 ───────────────────────────────────────────────
log "Instalando wkhtmltopdf..."
wget -q -O /tmp/wkhtmltox.rpm \
    https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6.1-2/wkhtmltox-0.12.6.1-2.almalinux9.aarch64.rpm
dnf install -y -q /tmp/wkhtmltox.rpm
rm -f /tmp/wkhtmltox.rpm
log "✓ wkhtmltopdf instalado"

# ── Passo 4: Usuário Odoo ─────────────────────────────────────────────────────
log "Criando usuário odoo..."
useradd -m -d /opt/odoo -s /bin/bash odoo 2>/dev/null || true
mkdir -p /opt/odoo/{logs,data,config,backups}
chown -R odoo:odoo /opt/odoo
log "✓ Usuário odoo criado"

# ── Passo 5: Repositório ──────────────────────────────────────────────────────
log "Clonando repositório..."
sudo -u odoo git clone --branch "${REPO_BRANCH}" --depth 1 \
    "${REPO_URL}" /opt/odoo/server
log "✓ Repositório clonado"

# ── Passo 6: Python venv ──────────────────────────────────────────────────────
log "Criando ambiente Python 3.11..."
sudo -u odoo python3.11 -m venv /opt/odoo/venv
sudo -u odoo /opt/odoo/venv/bin/pip install --upgrade pip wheel setuptools -q
sudo -u odoo /opt/odoo/venv/bin/pip install -r /opt/odoo/server/requirements.txt -q
log "✓ Ambiente Python configurado"

# ── Passo 7: odoo.conf ───────────────────────────────────────────────────────
log "Gerando configuração..."
ADMIN_PASSWD=$(python3 -c "import secrets; print(secrets.token_urlsafe(24))")

cat > /opt/odoo/config/odoo.conf <<CONF
[options]
http_port = 8069
longpolling_port = 8072
proxy_mode = True

db_host = 127.0.0.1
db_port = 5432
db_user = odoo
db_password = ${DB_PASS}
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

# Salva a senha master em arquivo seguro
echo "${ADMIN_PASSWD}" > /opt/odoo/config/.master_password
chmod 600 /opt/odoo/config/.master_password
log "✓ odoo.conf gerado (senha master salva em /opt/odoo/config/.master_password)"

# ── Passo 8: Serviço systemd ──────────────────────────────────────────────────
log "Configurando serviço systemd..."
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
log "✓ Serviço odoo configurado"

# ── Passo 9: Nginx ────────────────────────────────────────────────────────────
log "Instalando Nginx..."
dnf install -y -q nginx

cat > /etc/nginx/conf.d/odoo.conf <<NGINX
upstream odoo_backend { server 127.0.0.1:8069; }
upstream odoo_chat    { server 127.0.0.1:8072; }

server {
    listen 80;
    server_name ${DOMAIN};

    location /.well-known/acme-challenge/ { root /var/www/html; }

    client_max_body_size 128m;
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml;

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
log "✓ Nginx configurado"

# ── Passo 10: Firewall ────────────────────────────────────────────────────────
log "Configurando firewall..."
systemctl enable firewalld --now
firewall-cmd --permanent --add-service=http
firewall-cmd --permanent --add-service=https
firewall-cmd --permanent --add-service=ssh
firewall-cmd --reload
log "✓ Firewall configurado"

# ── Passo 11: SSL Let's Encrypt ───────────────────────────────────────────────
log "Configurando SSL..."
dnf install -y -q certbot python3-certbot-nginx
certbot --nginx \
    -d "${DOMAIN}" \
    --non-interactive \
    --agree-tos \
    -m "admin@${DOMAIN}" \
    --redirect
echo "0 3 * * * root certbot renew --quiet --post-hook 'systemctl reload nginx'" \
    > /etc/cron.d/certbot-renew
log "✓ SSL configurado"

# ── Passo 12: Backup automático ───────────────────────────────────────────────
log "Configurando backup..."
cat > /opt/odoo/backup_odoo.sh <<'BACKUP'
#!/bin/bash
set -euo pipefail
export PATH="/usr/pgsql-15/bin:$PATH"
export PGPASSWORD="Alex2201@"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/opt/odoo/backups"
mkdir -p "$BACKUP_DIR"
pg_dump -U odoo -h 127.0.0.1 odoo_prod | gzip > "${BACKUP_DIR}/db_${DATE}.sql.gz"
[ -d "/opt/odoo/data/filestore/odoo_prod" ] && \
    tar -czf "${BACKUP_DIR}/filestore_${DATE}.tar.gz" \
        -C /opt/odoo/data/filestore odoo_prod
find "$BACKUP_DIR" -name "*.gz" -mtime +14 -delete
echo "[$(date)] Backup: db_${DATE}.sql.gz"
BACKUP
chmod +x /opt/odoo/backup_odoo.sh
chown odoo:odoo /opt/odoo/backup_odoo.sh
echo "0 2 * * * root bash /opt/odoo/backup_odoo.sh >> /opt/odoo/logs/backup.log 2>&1" \
    > /etc/cron.d/odoo-backup
log "✓ Backup diário configurado"

# ── Passo 13: Inicializar banco e instalar módulos ────────────────────────────
log "Inicializando banco de dados Odoo..."
systemctl start odoo
sleep 15

log "Instalando módulos customizados..."
systemctl stop odoo
sudo -u odoo /opt/odoo/venv/bin/python3 /opt/odoo/server/odoo-bin \
    --config /opt/odoo/config/odoo.conf \
    --init theme_b24ui,hr_maestro_integration,project_maestro_timer,payment_maestro_setup \
    --stop-after-init \
    --log-level=warn
systemctl start odoo
log "✓ Módulos instalados"

# ── Resumo final ──────────────────────────────────────────────────────────────
MASTER_PASS=$(cat /opt/odoo/config/.master_password)

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║              ✅  INSTALAÇÃO CONCLUÍDA                   ║"
echo "╠══════════════════════════════════════════════════════════╣"
echo "║  🌐 URL         : https://${DOMAIN}"
echo "║  👤 Login       : admin"
echo "║  🔑 Senha master: ${MASTER_PASS}"
echo "║  🗄  Banco       : odoo_prod (usuário: odoo)"
echo "╠══════════════════════════════════════════════════════════╣"
echo "║  Logs    : journalctl -u odoo -f"
echo "║  Restart : systemctl restart odoo"
echo "║  Backup  : bash /opt/odoo/backup_odoo.sh"
echo "╚══════════════════════════════════════════════════════════╝"
SCRIPT_EOF
```

### 4.2 Executar o script no servidor

```bash
ssh -i ~/.ssh/odoo_oci -o StrictHostKeyChecking=no opc@${PUBLIC_IP} \
    "chmod +x /tmp/install_odoo.sh && sudo bash /tmp/install_odoo.sh 2>&1 | tee /tmp/install.log"
```

Aguardar ~15 minutos. O script exibirá o progresso em tempo real.

---

## FASE 5 — VERIFICAÇÃO FINAL

### 5.1 Buscar senha master gerada

```bash
MASTER_PASS=$(ssh -i ~/.ssh/odoo_oci opc@${PUBLIC_IP} \
    "sudo cat /opt/odoo/config/.master_password")
echo "Senha master: ${MASTER_PASS}"
```

### 5.2 Verificar todos os serviços

```bash
ssh -i ~/.ssh/odoo_oci opc@${PUBLIC_IP} "sudo bash -s" <<'CHECK'
echo "=== STATUS DOS SERVIÇOS ==="
systemctl is-active postgresql-15 && echo "✅ PostgreSQL ATIVO" || echo "❌ PostgreSQL FALHOU"
systemctl is-active odoo           && echo "✅ Odoo ATIVO"       || echo "❌ Odoo FALHOU"
systemctl is-active nginx          && echo "✅ Nginx ATIVO"      || echo "❌ Nginx FALHOU"
systemctl is-active firewalld      && echo "✅ Firewall ATIVO"   || echo "❌ Firewall FALHOU"

echo ""
echo "=== DISCO ==="
df -h / | tail -1

echo ""
echo "=== ÚLTIMAS LINHAS DO LOG ODOO ==="
journalctl -u odoo -n 10 --no-pager
CHECK
```

### 5.3 Testar HTTPS

```bash
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
    --max-time 15 "https://${DOMAIN}" 2>/dev/null || echo "000")

if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "303" ]; then
    echo "✅ Site respondendo em https://${DOMAIN} (HTTP ${HTTP_CODE})"
else
    echo "❌ Site não responde (HTTP ${HTTP_CODE})"
    echo "Verificar logs: journalctl -u odoo -n 50"
fi
```

---

## FASE 6 — RELATÓRIO FINAL

O agente deve reportar ao final:

```
╔══════════════════════════════════════════════════════════════╗
║            ODOO 19 — IMPLANTAÇÃO CONCLUÍDA                  ║
╠══════════════════════════════════════════════════════════════╣
║  INFRAESTRUTURA OCI                                          ║
║  ├─ Instância  : VM.Standard.A1.Flex (4 OCPU / 24GB ARM)   ║
║  ├─ SO         : Oracle Linux 9                              ║
║  ├─ IP Público : <IP>                                        ║
║  └─ OCID       : <INSTANCE_ID>                               ║
╠══════════════════════════════════════════════════════════════╣
║  ACESSO AO SISTEMA                                           ║
║  ├─ URL        : https://<IP>.nip.io                        ║
║  ├─ Login      : admin                                       ║
║  └─ Senha master: <MASTER_PASS>                              ║
╠══════════════════════════════════════════════════════════════╣
║  SERVIÇOS                                                    ║
║  ├─ ✅ PostgreSQL 15                                         ║
║  ├─ ✅ Odoo 19 (systemd)                                    ║
║  ├─ ✅ Nginx + SSL Let's Encrypt                             ║
║  └─ ✅ Backup diário (02h00)                                 ║
╠══════════════════════════════════════════════════════════════╣
║  MÓDULOS INSTALADOS                                          ║
║  ├─ ✅ theme_b24ui                                           ║
║  ├─ ✅ hr_maestro_integration                                ║
║  ├─ ✅ project_maestro_timer                                 ║
║  └─ ✅ payment_maestro_setup                                 ║
╠══════════════════════════════════════════════════════════════╣
║  CHAVE SSH SALVA EM                                          ║
║  └─ ~/.ssh/odoo_oci  (guardar em local seguro)              ║
╚══════════════════════════════════════════════════════════════╝
```

---

## TRATAMENTO DE ERROS

| Erro | Solução |
|------|---------|
| `SSH connection refused` | Aguardar mais 2 minutos e tentar novamente |
| `certbot: domain not resolving` | Confirmar que o IP está correto e portas 80/443 abertas na Security List |
| `Odoo service failed` | `journalctl -u odoo -n 50` para ver o erro específico |
| `PostgreSQL auth failed` | Verificar `/var/lib/pgsql/15/data/pg_hba.conf` |
| `Module not found` | Verificar `addons_path` no `odoo.conf` e se o repo foi clonado corretamente |
| `Always Free limit` | Erro da OCI se já existirem 4 instâncias ARM ativas na conta |

---

## COMANDOS ÚTEIS PÓS-INSTALAÇÃO

```bash
# Acessar o servidor
ssh -i ~/.ssh/odoo_oci opc@${PUBLIC_IP}

# Ver logs em tempo real
sudo journalctl -u odoo -f

# Reiniciar Odoo
sudo systemctl restart odoo

# Atualizar módulo específico
sudo systemctl stop odoo
sudo -u odoo /opt/odoo/venv/bin/python3 /opt/odoo/server/odoo-bin \
    -c /opt/odoo/config/odoo.conf \
    -u nome_do_modulo --stop-after-init
sudo systemctl start odoo

# Backup manual
sudo bash /opt/odoo/backup_odoo.sh

# Ver backups
ls -lh /opt/odoo/backups/
```
