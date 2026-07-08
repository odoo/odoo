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

RUN useradd --create-home --home-dir /var/lib/odoo --shell /bin/bash odoo \
    && mkdir -p /etc/odoo /mnt/extra-addons /var/log/odoo \
    && chown -R odoo:odoo /etc/odoo /mnt/extra-addons /var/lib/odoo /var/log/odoo

WORKDIR /opt/odoo

COPY requirements.txt .
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
