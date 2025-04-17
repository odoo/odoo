FROM python:3.10-slim

# Install dependencies needed by Odoo
RUN apt-get update && apt-get install -y \
    build-essential \
    wget \
    git \
    python3-dev \
    libldap2-dev \
    libsasl2-dev \
    libpq-dev \
    libxml2-dev \
    libxslt1-dev \
    libzip-dev \
    libjpeg62-turbo-dev \
    liblcms2-dev \
    libblas-dev \
    libatlas-base-dev \
    libssl-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .

RUN pip install --upgrade pip setuptools wheel
RUN pip install -r requirements.txt

EXPOSE 8069
CMD ["python3", "odoo-bin", "-c", "odoo.conf"]
