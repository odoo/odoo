FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=en_US.UTF-8 \
    LC_ALL=en_US.UTF-8 \
    PATH="/opt/odoo/venv/bin:$PATH"

# ── System packages ──────────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates curl gnupg locales \
    && locale-gen en_US.UTF-8 \
    # Node.js 20 LTS
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends \
        nodejs \
        build-essential \
        python3 python3-dev python3-venv \
        libpq-dev \
        libxml2-dev libxslt1-dev \
        libsasl2-dev libldap2-dev \
        libjpeg-dev libpng-dev libtiff5-dev \
        libssl-dev libffi-dev \
        fonts-liberation fonts-noto-cjk \
        wkhtmltopdf \
    && npm install -g rtlcss \
    && rm -rf /var/lib/apt/lists/*

# ── System user ──────────────────────────────────────────────────────────────
RUN useradd -m -d /opt/odoo -U -r -s /bin/bash odoo

# ── Python virtual environment ───────────────────────────────────────────────
# Ubuntu 24.04 enforces PEP 668 (no system-wide pip installs), so we use a venv.
# PATH above makes the venv active for all subsequent RUN/CMD/ENTRYPOINT steps.
RUN python3 -m venv /opt/odoo/venv \
    && pip install --upgrade pip setuptools wheel

# ── Copy source and install Python requirements ──────────────────────────────
WORKDIR /opt/odoo/server
COPY --chown=odoo:odoo . .

RUN pip install --no-cache-dir -r requirements.txt \
    && mkdir -p /var/log/odoo /var/lib/odoo /etc/odoo \
    && chown -R odoo:odoo /opt/odoo /var/log/odoo /var/lib/odoo /etc/odoo \
    && chmod +x /opt/odoo/server/docker/entrypoint.sh

USER odoo

EXPOSE 8069 8072

ENTRYPOINT ["/opt/odoo/server/docker/entrypoint.sh"]
CMD ["/opt/odoo/server/odoo-bin", "-c", "/etc/odoo/odoo.conf"]
