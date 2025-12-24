# syntax=docker/dockerfile:1.7

############################
# 1) Builder: wheels Python
############################
FROM python:3.12-slim-bookworm AS builder

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    curl \
    ca-certificates \
    libpq-dev \
    libsasl2-dev \
    libldap2-dev \
    libxml2-dev \
    libxslt1-dev \
    zlib1g-dev \
    libjpeg-dev \
    libfreetype6-dev \
    liblcms2-dev \
    libopenjp2-7-dev \
    libtiff6 \
    libwebp-dev \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/odoo

# Copie só o requirements primeiro pra cache de build
COPY ./requirements.txt ./requirements.txt

# Builda wheels (mais rápido e reprodutível no runtime)
RUN python -m pip install --upgrade pip wheel setuptools \
 && python -m pip wheel -r requirements.txt -w /wheels


############################
# 2) Runtime
############################
FROM python:3.12-slim-bookworm AS runtime

ENV DEBIAN_FRONTEND=noninteractive \
    ODOO_HOME=/opt/odoo \
    ODOO_DATA_DIR=/var/lib/odoo \
    ODOO_EXTRA_ADDONS=/mnt/extra-addons \
    ODOO_CONF=/etc/odoo/odoo.conf \
    WKHTMLTOPDF_VERSION=0.12.6.1-3

# Runtime libs (sem *-dev)
RUN apt-get update && apt-get install -y --no-install-recommends \
    tini \
    curl \
    ca-certificates \
    gosu \
    libpq5 \
    libsasl2-2 \
    libldap-2.5-0 \
    libxml2 \
    libxslt1.1 \
    zlib1g \
    libjpeg62-turbo \
    libfreetype6 \
    liblcms2-2 \
    libopenjp2-7 \
    libtiff6 \
    libwebp7 \
    fontconfig \
    fonts-dejavu-core \
    fonts-liberation \
    nodejs \
    npm \
 && rm -rf /var/lib/apt/lists/*

# Less compiler + minificador CSS (assets)
RUN npm install -g less less-plugin-clean-css

# wkhtmltopdf patched (Qt) - recomendado pro Odoo 19 p/ headers/footers
# Usa pacote bookworm da release wkhtmltopdf/packaging
ARG TARGETARCH
RUN set -eux; \
    if [ "$TARGETARCH" = "amd64" ]; then \
      DEB="wkhtmltox_${WKHTMLTOPDF_VERSION}.bookworm_amd64.deb"; \
    elif [ "$TARGETARCH" = "arm64" ]; then \
      DEB="wkhtmltox_${WKHTMLTOPDF_VERSION}.bookworm_arm64.deb"; \
    else \
      echo "Unsupported arch: $TARGETARCH" && exit 1; \
    fi; \
    curl -fSL -o /tmp/wkhtml.deb "https://github.com/wkhtmltopdf/packaging/releases/download/${WKHTMLTOPDF_VERSION}/${DEB}"; \
    apt-get update; \
    apt-get install -y --no-install-recommends /tmp/wkhtml.deb; \
    rm -f /tmp/wkhtml.deb; \
    rm -rf /var/lib/apt/lists/*

# cria usuário
RUN useradd -m -d /home/odoo -s /bin/bash odoo \
 && mkdir -p ${ODOO_HOME} ${ODOO_DATA_DIR} ${ODOO_EXTRA_ADDONS} /etc/odoo \
 && chown -R odoo:odoo ${ODOO_HOME} ${ODOO_DATA_DIR} ${ODOO_EXTRA_ADDONS} /etc/odoo

WORKDIR ${ODOO_HOME}

# instala wheels
COPY --from=builder /wheels /wheels
COPY --from=builder /opt/odoo/requirements.txt /opt/odoo/requirements.txt
RUN python -m pip install --no-index --find-links=/wheels -r /opt/odoo/requirements.txt \
 && rm -rf /wheels

# copia o código do odoo + seus addons
COPY ./odoo-bin ./odoo-bin
COPY ./odoo ./odoo
COPY ./addons ./addons
COPY ./enabled-addons ${ODOO_EXTRA_ADDONS}

# Clone OCA repos necessários
RUN git clone -b 19.0 --depth 1 https://github.com/OCA/storage.git /tmp/oca-storage \
 && cp -r /tmp/oca-storage/fs_storage ${ODOO_EXTRA_ADDONS}/ \
 && cp -r /tmp/oca-storage/fs_attachment ${ODOO_EXTRA_ADDONS}/ \
 && cp -r /tmp/oca-storage/fs_attachment_s3 ${ODOO_EXTRA_ADDONS}/ \
 && rm -rf /tmp/oca-storage \
 && chown -R odoo:odoo ${ODOO_EXTRA_ADDONS}

# entrypoint (tini + roda como odoo)
COPY ./deploy/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh \
 && chown odoo:odoo /entrypoint.sh

EXPOSE 8069 8072

# volumes (k8s vai montar)
VOLUME ["/var/lib/odoo", "/mnt/extra-addons", "/etc/odoo"]

ENTRYPOINT ["/usr/bin/tini", "--", "/entrypoint.sh"]
CMD ["python", "/opt/odoo/odoo-bin", "-c", "/etc/odoo/odoo.conf"]