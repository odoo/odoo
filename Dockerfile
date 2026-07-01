FROM python:3.11-slim-bookworm

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    libpq-dev \
    libxml2-dev \
    libxslt1-dev \
    libldap2-dev \
    libsasl2-dev \
    libjpeg-dev \
    libwebp-dev \
    libevent-dev \
    libffi-dev \
    zlib1g-dev \
    libharfbuzz-dev \
    libfribidi-dev \
    libxcb1-dev \
    node-less \
    npm \
    wait-for-it \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install wkhtmltopdf
RUN curl -o wkhtmltox.deb -sSL https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6.1-2/wkhtmltox_0.12.6.1-2.bullseye_amd64.deb \
    && apt-get update && apt-get install -y --no-install-recommends ./wkhtmltox.deb \
    && apt-get clean && rm -rf /var/lib/apt/lists/* && rm wkhtmltox.deb

# Create odoo user
RUN useradd -m -d /opt/odoo -s /bin/bash odoo

# Set working directory
WORKDIR /opt/odoo

# Copy requirements and install
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Set permissions
RUN chown -R odoo:odoo /opt/odoo

# Create directory for data
RUN mkdir -p /var/lib/odoo && chown -R odoo:odoo /var/lib/odoo
VOLUME ["/var/lib/odoo"]

# Expose port
EXPOSE 8069 8071 8072

# Default environment variables
ENV ODOO_RC /etc/odoo/odoo.conf

USER odoo

ENTRYPOINT ["python3", "odoo-bin"]
CMD ["-c", "/etc/odoo/odoo.conf"]
