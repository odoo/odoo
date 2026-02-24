FROM python:3.12-bookworm

SHELL ["/bin/bash", "-xo", "pipefail", "-c"]

# Generate locale C.UTF-8 for postgres and general locale data
ENV LANG=C.UTF-8

# Install system dependencies
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
        python3-magic \
        python3-num2words \
        python3-odf \
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
        libldap2-dev \
        libpq-dev \
        libsasl2-dev \
    && rm -rf /var/lib/apt/lists/*

# Install wkhtmltopdf
RUN curl -o wkhtmltox.deb -sSL https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6.1-3/wkhtmltox_0.12.6.1-3.bookworm_amd64.deb \
    && apt-get update \
    && apt-get install -y --no-install-recommends ./wkhtmltox.deb \
    && rm -rf /var/lib/apt/lists/* wkhtmltox.deb

# Install rtlcss (for right-to-left language support)
RUN npm install -g rtlcss

# Create odoo user
RUN useradd -ms /bin/bash odoo

# Copy Odoo source
COPY . /opt/odoo
WORKDIR /opt/odoo

# Install Python dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# Create necessary directories
RUN mkdir -p /var/lib/odoo /var/log/odoo /mnt/extra-addons \
    && chown -R odoo:odoo /var/lib/odoo /var/log/odoo /mnt/extra-addons /opt/odoo

# Switch to odoo user
USER odoo

EXPOSE 8069 8072

ENTRYPOINT ["python3", "/opt/odoo/odoo-bin"]
CMD ["--config=/etc/odoo/odoo.conf"]
