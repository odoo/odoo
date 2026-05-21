# syntax=docker/dockerfile:1.6
#
# Dockerfile for deploying Odoo 19.0 on Railway (https://railway.com).
#
# Railway exposes:
#   - $PORT          : the public HTTP port the container must listen on
#   - $DATABASE_URL  : postgres connection string when a Postgres plugin is attached
#                      (format: postgresql://user:password@host:port/dbname)
#
# The entrypoint translates these into Odoo configuration before launching
# odoo-bin. Persistent state (filestore, sessions) lives under /var/lib/odoo,
# which should be mounted on a Railway Volume for production deployments.

FROM ubuntu:noble

LABEL org.opencontainers.image.title="Odoo"
LABEL org.opencontainers.image.description="Odoo 19.0 image tailored for Railway deployments"
LABEL org.opencontainers.image.source="https://github.com/odoo/odoo"
LABEL org.opencontainers.image.licenses="LGPL-3.0"

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    ODOO_RC=/etc/odoo/odoo.conf

# Drop the default `ubuntu` user shipped with noble so we can recreate uid 1000
# for the odoo service account.
RUN userdel -r ubuntu 2>/dev/null || true

# System packages: PostgreSQL client, the Python deps Odoo expects (mirroring
# debian/control), and fonts/utilities needed for PDF rendering.
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        gnupg \
        locales \
        tzdata \
    && locale-gen C.UTF-8 \
    && update-locale LANG=C.UTF-8 \
    && apt-get install -y --no-install-recommends \
        adduser \
        fonts-dejavu-core \
        fonts-font-awesome \
        fonts-freefont-ttf \
        fonts-inconsolata \
        fonts-noto-core \
        fonts-roboto-unhinted \
        gsfonts \
        git \
        libjs-underscore \
        libpq-dev \
        node-less \
        postgresql-client \
        python3 \
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
        python3-jinja2 \
        python3-ldap \
        python3-libsass \
        python3-lxml \
        python3-lxml-html-clean \
        python3-magic \
        python3-markupsafe \
        python3-num2words \
        python3-ofxparse \
        python3-openpyxl \
        python3-openssl \
        python3-passlib \
        python3-pil \
        python3-pip \
        python3-polib \
        python3-psutil \
        python3-psycopg2 \
        python3-pypdf2 \
        python3-qrcode \
        python3-renderpm \
        python3-reportlab \
        python3-requests \
        python3-rjsmin \
        python3-serial \
        python3-setuptools \
        python3-stdnum \
        python3-tz \
        python3-urllib3 \
        python3-usb \
        python3-vobject \
        python3-werkzeug \
        python3-xlrd \
        python3-xlsxwriter \
        python3-zeep \
    && rm -rf /var/lib/apt/lists/*

# wkhtmltopdf 0.12.6.1 patched-qt is the version Odoo officially supports for
# PDF reports. The build is published per-distro from the wkhtmltopdf project.
# The jammy (22.04) build runs fine on noble (24.04).
RUN set -eux; \
    arch="$(dpkg --print-architecture)"; \
    case "$arch" in \
        amd64) pkg="wkhtmltox_0.12.6.1-3.jammy_amd64.deb" ;; \
        arm64) pkg="wkhtmltox_0.12.6.1-3.jammy_arm64.deb" ;; \
        *) echo "Unsupported arch: $arch" >&2; exit 1 ;; \
    esac; \
    curl -fsSL -o /tmp/wkhtml.deb "https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6.1-3/${pkg}"; \
    apt-get update; \
    apt-get install -y --no-install-recommends /tmp/wkhtml.deb; \
    rm -f /tmp/wkhtml.deb; \
    rm -rf /var/lib/apt/lists/*; \
    wkhtmltopdf --version

# Service account.
RUN groupadd -r odoo --gid=1000 \
    && useradd -r -g odoo --uid=1000 --home-dir=/var/lib/odoo --shell=/bin/bash odoo \
    && install -d -o odoo -g odoo /var/lib/odoo /var/log/odoo /etc/odoo /mnt/extra-addons

WORKDIR /opt/odoo

# Copy source. .dockerignore keeps build context small.
COPY --chown=odoo:odoo . /opt/odoo

# Make odoo-bin reachable on $PATH. We skip `pip install` to keep the
# apt-installed Python deps as the single source of truth (avoids the
# noble PEP 668 externally-managed-environment issue and prevents pip
# from yanking newer versions over the distro ones). odoo-bin's shebang
# plus PYTHONPATH = /opt/odoo is enough for `import odoo` to resolve.
ENV PYTHONPATH=/opt/odoo
RUN ln -sf /opt/odoo/odoo-bin /usr/local/bin/odoo

COPY docker/odoo.conf /etc/odoo/odoo.conf
COPY docker/entrypoint.sh /usr/local/bin/entrypoint
RUN chmod +x /usr/local/bin/entrypoint \
    && chown odoo:odoo /etc/odoo/odoo.conf

VOLUME ["/var/lib/odoo", "/mnt/extra-addons"]

# Railway routes traffic to whichever port the process binds to (via $PORT).
# 8069 is documented for local docker runs; the entrypoint honours $PORT first.
EXPOSE 8069

USER odoo

ENTRYPOINT ["/usr/local/bin/entrypoint"]
CMD ["odoo"]
