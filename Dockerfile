FROM debian:buster-slim

SHELL ["/bin/bash", "-xo", "pipefail", "-c"] 
# Generate locale C.UTF-8 for postgres and general locale data
ENV LANG C.UTF-8

#Adding odo user
RUN adduser --system --quiet --shell=/bin/bash --no-create-home --gecos 'ODOO' --group odoo

# Install some deps, lessc and less-plugin-clean-css, and wkhtmltopdf
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        dirmngr \
        fonts-noto-cjk \
        gnupg \
        libssl-dev \
        node-less \
        npm \
        gcc\
        file \
        make \
        libxml2-dev \
        libxslt1-dev \
        libldap2-dev \
        libsasl2-dev \
        libtiff5-dev \
        libevent-dev \
        libjpeg62-turbo-dev\
        libopenjp2-7-dev \
        zlib1g-dev \
        libfreetype6-dev \
        liblcms2-dev \
        libwebp-dev \
        libharfbuzz-dev \
        libfribidi-dev \
        libxcb1-dev \
        libpq-dev \
        python3-dev \
        python3-num2words \
        python3-pdfminer \
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
RUN echo 'deb http://apt.postgresql.org/pub/repos/apt/ buster-pgdg main' > /etc/apt/sources.list.d/pgdg.list \
    && GNUPGHOME="$(mktemp -d)" \
    && export GNUPGHOME \
    && repokey='B97B0AFCAA1A47F044F244A07FCC7D46ACCC4CF8' \
    && gpg --batch --keyserver keyserver.ubuntu.com --recv-keys "${repokey}" \
    && gpg --batch --armor --export "${repokey}" > /etc/apt/trusted.gpg.d/pgdg.gpg.asc \
    && gpgconf --kill all \
    && rm -rf "$GNUPGHOME" \
    && apt-get update  \
    && apt-get install --no-install-recommends -y postgresql-client \
    && rm -f /etc/apt/sources.list.d/pgdg.list \
    && rm -rf /var/lib/apt/lists/*


# Install rtlcss (on Debian buster)
RUN npm install -g rtlcss

# Set permissions and Mount /var/lib/odoo to allow restoring filestore and /odoo/extra-addons for users addons
ENV ODOO_SRC odoo
RUN    mkdir -p /opt/odoo/extra-addons \
    && mkdir -p /var/lib/odoo \
    && mkdir -p /opt/odoo/data \
    && mkdir -p /opt/odoo/config \
    && chown -R odoo:odoo /opt/odoo/data \
    && chown -R odoo:odoo /var/lib/odoo \
    && chown -R odoo:odoo /opt/odoo 

VOLUME ["/opt/odoo/data", "/opt/odoo/extra-addons", "var/lib/odoo"]

# Install Odoo
ENV ODOO_VERSION 14.0

COPY --chown=odoo:odoo . /opt/odoo/odoo

WORKDIR /opt/odoo/odoo
RUN pip3 install setuptools wheel && pip3 install -r requirements.txt

# Expose Odoo services
EXPOSE 8069 8071 8072


# Set the default config file
ENV ODOO_RC /opt/odoo/odoo/odoo.conf
RUN ln -s /opt/odoo/odoo/odoo-bin /usr/bin/odoo
USER odoo

ENTRYPOINT ["/opt/odoo/odoo/entrypoint.sh"]
CMD ["odoo"]

