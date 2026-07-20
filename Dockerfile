FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    ODOO_RC=/etc/odoo/odoo.conf

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        ca-certificates \
        curl \
        fonts-dejavu-core \
        fonts-liberation \
        gettext \
        git \
        libevent-dev \
        libfreetype6-dev \
        libjpeg62-turbo-dev \
        libldap2-dev \
        libpq-dev \
        libsasl2-dev \
        libssl-dev \
        libxml2-dev \
        libxslt1-dev \
        node-less \
        npm \
        postgresql-client \
        python3-dev \
        zlib1g-dev \
    && npm install -g rtlcss \
    && apt-get purge -y --auto-remove npm \
    && rm -rf /var/lib/apt/lists/*

# wkhtmltopdf — the patched-Qt build Odoo needs to render PDF reports (headers/
# footers). Without it Odoo falls back to HTML. Debian bookworm package; swap the
# asset for the arm64 one if you build on Apple Silicon.
RUN curl -sSL -o /tmp/wkhtmltox.deb \
        https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6.1-3/wkhtmltox_0.12.6.1-3.bookworm_amd64.deb \
    && apt-get update \
    && apt-get install -y --no-install-recommends /tmp/wkhtmltox.deb \
    && rm -rf /var/lib/apt/lists/* /tmp/wkhtmltox.deb

RUN useradd --create-home --home-dir /var/lib/odoo --shell /bin/bash odoo \
    && mkdir -p /etc/odoo /mnt/custom_addons /var/log/odoo \
    && chown -R odoo:odoo /etc/odoo /mnt/custom_addons /var/lib/odoo /var/log/odoo

WORKDIR /opt/odoo

COPY requirements.txt .
# Do not add `inotify` here to enable --dev=reload. Odoo watches every addons path
# recursively (~620 modules); over a Docker Desktop bind mount that hangs boot, and
# Windows host writes never raise inotify events in the Linux VM anyway. Restart the
# container after Python edits instead.
RUN pip install --upgrade pip setuptools wheel \
    && pip install -r requirements.txt

COPY . .
RUN pip install -e .

COPY docker/odoo.conf /etc/odoo/odoo.conf
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh \
    && chown -R odoo:odoo /opt/odoo /etc/odoo

USER odoo

EXPOSE 8069 8072

ENTRYPOINT ["/entrypoint.sh"]
CMD ["python", "odoo-bin", "-c", "/etc/odoo/odoo.conf"]
