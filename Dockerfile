FROM debian:buster-slim
MAINTAINER Odoo S.A. <info@odoo.com>

SHELL ["/bin/bash", "-xo", "pipefail", "-c"]

# Generate locale C.UTF-8 for postgres and general locale data
ENV LANG C.UTF-8

# Install some deps, lessc and less-plugin-clean-css, and wkhtmltopdf
RUN apt-get update \
  && apt-get install -y --no-install-recommends \
  ca-certificates \
  curl \
  dirmngr \
  fonts-noto-cjk \
  gnupg \
  libssl-dev \
  node-less \
  npm \
  python3-num2words \
  python3-pip \
  python3-phonenumbers \
  python3-pyldap \
  python3-qrcode \
  python3-renderpm \
  python3-setuptools \
  python3-slugify \
  python3-vobject \
  python3-watchdog \
  python3-xlrd \
  python3-xlwt \
  xz-utils \
  && curl -o wkhtmltox.deb -sSL https://github.com/wkhtmltopdf/wkhtmltopdf/releases/download/0.12.5/wkhtmltox_0.12.5-1.buster_amd64.deb \
  && echo 'ea8277df4297afc507c61122f3c349af142f31e5 wkhtmltox.deb' | sha1sum -c - \
  && apt-get install -y --no-install-recommends ./wkhtmltox.deb \
  && rm -rf /var/lib/apt/lists/* wkhtmltox.deb

# install latest postgresql-client
# RUN echo 'deb http://apt.postgresql.org/pub/repos/apt/ buster-pgdg main' > /etc/apt/sources.list.d/pgdg.list \
#   && GNUPGHOME="$(mktemp -d)" \
#   && export GNUPGHOME \
#   && repokey='B97B0AFCAA1A47F044F244A07FCC7D46ACCC4CF8' \
#   && gpg --batch --keyserver keyserver.ubuntu.com --recv-keys "${repokey}" \
#   && gpg --batch --armor --export "${repokey}" > /etc/apt/trusted.gpg.d/pgdg.gpg.asc \
#   && gpgconf --kill all \
#   && rm -rf "$GNUPGHOME" \
#   && apt-get update  \
#   && apt-get install --no-install-recommends -y postgresql-client \
#   && rm -f /etc/apt/sources.list.d/pgdg.list \
#   && rm -rf /var/lib/apt/lists/*

# Install rtlcss (on Debian buster)
RUN npm install -g rtlcss

# Install rexray efs plugin for docker volumes mount:
RUN apt-get update \
  && apt-get -y install git binutils

# Install Odoo
ENV ODOO_VERSION 13.0
ARG ODOO_RELEASE=20201123
ARG ODOO_SHA=1af64956f215ba0a2991ac6c86b98610c480c17b
RUN curl -o odoo.deb -sSL http://nightly.odoo.com/${ODOO_VERSION}/nightly/deb/odoo_${ODOO_VERSION}.${ODOO_RELEASE}_all.deb \
  && echo "${ODOO_SHA} odoo.deb" | sha1sum -c - \
  && apt-get update \
  && apt-get -y install --no-install-recommends ./odoo.deb \
  && rm -rf /var/lib/apt/lists/* odoo.deb

# Copy entrypoint script and Odoo configuration file
COPY ./entrypoint.sh /
COPY ./efs.sh /
# COPY ./mnt/config/odoo.conf /etc/odoo/

# Set permissions and Mount /var/lib/odoo to allow restoring filestore and /mnt/extra-addons for users addons
RUN mkdir -p /mnt/extra-addons \
  && chown -R odoo /mnt/extra-addons
  && chown odoo /etc/odoo.conf \

#/var/lib/odoo : filestore  
VOLUME ["/var/lib/odoo", "/mnt/extra-addons", "/etc/odoo"]
#https://www.odoo.com/es_ES/forum/ayuda-1/install-addons-on-docker-version-of-odoo-13-175798

# Expose Odoo services
EXPOSE 8069 8071 8072

# Set the default config file
ENV ODOO_RC /etc/odoo.conf

#Descomentar cuando pueda arreglarlo:
COPY wait-for-psql.py /usr/local/bin/wait-for-psql.py

#custom addons
# COPY ./custom-addons /opt/addons

# Set default user when running the container
USER odoo

ENTRYPOINT ["/entrypoint.sh"]
CMD ["odoo"]