FROM python:3.11-slim

# Install dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        python3-dev \
        libxml2-dev \
        libxslt1-dev \
        libldap2-dev \
        libsasl2-dev \
        libpq-dev \
        libjpeg-dev \
        libpng-dev \
        libffi-dev \
        libssl-dev \
        node-less \
        npm \
        git \
        wget \
        xz-utils \
        && rm -rf /var/lib/apt/lists/*

# Set workdir
WORKDIR /mnt/odoo

# Copy requirements and install python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy only necessary files
COPY odoo-bin ./
COPY odoo/ ./odoo/
COPY addons/ ./addons/

# Create log directory
RUN mkdir -p /var/log/odoo

# Expose Odoo port
EXPOSE 8069

CMD ["./odoo-bin", "-c", "/etc/odoo/odoo.conf"]
