FROM python:3.12-slim-bookworm

# 1. Install necessary Linux system dependencies for Odoo
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libxml2-dev \
    libxslt1-dev \
    libldap2-dev \
    libsasl2-dev \
    libssl-dev \
    libjpeg-dev \
    zlib1g-dev \
    wkhtmltopdf \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 2. Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir psycopg2-binary

# 3. Copy project files into container
COPY . .

# 4. Prepare data directory and set execution permissions on entrypoint
RUN mkdir -p /app/data && chmod +x /app/entrypoint.sh

# 5. Expose default port
EXPOSE 8069

# 6. Start Odoo using the deployment entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]
