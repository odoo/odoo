# syntax=docker/dockerfile:1.7

ARG PYTHON_VERSION=3.12
ARG DEBIAN_VERSION=bookworm

FROM python:${PYTHON_VERSION}-slim-${DEBIAN_VERSION} AS base

ENV LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

# System deps required to build/install python wheels (psycopg2, lxml, pillow, etc.)
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    git \
    build-essential \
    gcc \
    libpq-dev \
    libsasl2-dev \
    libldap2-dev \
    libssl-dev \
    libffi-dev \
    libxml2-dev \
    libxslt1-dev \
    zlib1g-dev \
    libjpeg-dev \
    libfreetype6-dev \
    liblcms2-dev \
    libwebp-dev \
    libopenjp2-7-dev \
    libtiff5-dev \
    libharfbuzz-dev \
    libfribidi-dev \
    gettext-base \
    postgresql-client \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/odoo

# Install python deps first for layer caching
COPY requirements.txt /opt/odoo/requirements.txt
RUN python -m pip install --upgrade pip \
 && pip install -r /opt/odoo/requirements.txt

# Copy Odoo source (core + official addons) and infra folders
COPY odoo /opt/odoo/odoo
COPY addons /opt/odoo/addons
COPY odoo-bin /opt/odoo/odoo-bin
COPY setup.py setup.cfg MANIFEST.in LICENSE COPYRIGHT /opt/odoo/

# Optional custom addons baked in the image (dev will mount over it)
COPY custom_addons /opt/odoo/custom_addons

# Optional OCA addons baked in the image (dev/prod can mount over it)
COPY oca_addons /opt/odoo/oca_addons

# Default configuration template (can be overridden by bind-mount)
COPY config/odoo.conf.template /etc/odoo/odoo.conf.template

# Runtime directories
RUN mkdir -p /var/lib/odoo /etc/odoo \
 && useradd -m -d /var/lib/odoo -U -r -s /bin/bash odoo \
 && chown -R odoo:odoo /var/lib/odoo /opt/odoo /etc/odoo

COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8069 8072

USER odoo

ENTRYPOINT ["/entrypoint.sh"]

FROM base AS dev

# In dev we keep everything the same but default to dev mode
CMD ["python", "/opt/odoo/odoo-bin", "-c", "/etc/odoo/odoo.conf", "--dev=all"]

FROM base AS prod

CMD ["python", "/opt/odoo/odoo-bin", "-c", "/etc/odoo/odoo.conf"]
