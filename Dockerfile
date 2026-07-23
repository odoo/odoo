# syntax=docker/dockerfile:1
# =============================================================================
# aidt-odoo — production image built from this source tree
# Stages:
#   builder — compiles Python dependencies into a virtualenv
#   runtime — slim production image (default target)
#   dev     — runtime + developer tooling; source is bind-mounted at run time
# =============================================================================

# ----------------------------------------------------------------------------
# Stage 1: build Python dependencies
# ----------------------------------------------------------------------------
FROM python:3.12-slim-bookworm AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libffi-dev \
        libjpeg-dev \
        libldap2-dev \
        libpq-dev \
        libsasl2-dev \
        libssl-dev \
        libxml2-dev \
        libxslt1-dev \
        pkg-config \
        zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt /tmp/requirements.txt
RUN pip install --upgrade pip wheel \
    && pip install -r /tmp/requirements.txt

# ----------------------------------------------------------------------------
# Stage 2: production runtime
# ----------------------------------------------------------------------------
FROM python:3.12-slim-bookworm AS runtime

ENV PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

# Runtime libraries, fonts, tools
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        fonts-dejavu-core \
        fonts-liberation \
        fonts-noto-cjk \
        gettext-base \
        libjpeg62-turbo \
        libldap-2.5-0 \
        libpq5 \
        libsasl2-2 \
        libxml2 \
        libxslt1.1 \
        nodejs \
        npm \
        postgresql-client \
        zlib1g \
    && rm -rf /var/lib/apt/lists/*

# wkhtmltopdf (patched Qt build — required for PDF report headers/footers)
RUN curl -fsSL -o /tmp/wkhtmltox.deb \
        "https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6.1-3/wkhtmltox_0.12.6.1-3.bookworm_$(dpkg --print-architecture).deb" \
    && apt-get update \
    && apt-get install -y --no-install-recommends /tmp/wkhtmltox.deb \
    && rm -rf /tmp/wkhtmltox.deb /var/lib/apt/lists/*

# rtlcss for right-to-left language asset generation
RUN npm install -g rtlcss

# Non-root user; fixed uid keeps volume ownership stable across rebuilds
RUN groupadd -g 101 odoo \
    && useradd -r -u 101 -g odoo -d /var/lib/odoo -s /usr/sbin/nologin odoo \
    && mkdir -p /var/lib/odoo /etc/odoo /opt/odoo \
    && chown -R odoo:odoo /var/lib/odoo /etc/odoo /opt/odoo

COPY --from=builder /opt/venv /opt/venv

# Odoo source (production bakes the source into the image)
COPY --chown=odoo:odoo . /opt/odoo

COPY --chown=odoo:odoo docker/odoo.conf /etc/odoo/odoo.conf.template
COPY --chmod=755 docker/entrypoint.sh /entrypoint.sh

USER odoo
WORKDIR /opt/odoo

VOLUME ["/var/lib/odoo"]
EXPOSE 8069 8072

HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD curl -fsS http://localhost:8069/web/health || exit 1

ENTRYPOINT ["/entrypoint.sh"]
CMD ["odoo"]

# ----------------------------------------------------------------------------
# Stage 3: development (bind-mount the source over /opt/odoo)
# ----------------------------------------------------------------------------
FROM runtime AS dev

USER root
# watchdog: enables --dev=reload auto-restart; debugpy: remote debugging (VS Code attach)
RUN pip install --no-cache-dir debugpy watchdog ipython
USER odoo
