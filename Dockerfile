# Use a lightweight base Python image
FROM python:3.9-slim

# Set environment variables
ENV LANG C.UTF-8
ENV LC_ALL C.UTF-8

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libssl-dev \
    libffi-dev \
    libxml2-dev \
    libxslt1-dev \
    zlib1g-dev \
    libsasl2-dev \
    libldap2-dev \
    libpq-dev \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy only the requirements file first to leverage Docker cache
COPY requirements.txt .

# Uninstall pre-installed XlsxWriter and install Python dependencies
RUN pip uninstall -y XlsxWriter || true
RUN pip install --no-cache-dir --ignore-installed -r requirements.txt

# Ensure necessary Odoo directories exist
RUN mkdir -p /var/lib/odoo/filestore

# Copy the rest of the application
COPY . .

# Copy the entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Expose the Odoo default port
EXPOSE 8069

# Set entrypoint
ENTRYPOINT ["/entrypoint.sh"]
