# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Only copy and install dependencies first (Docker caching benefit)
COPY requirements.txt requirements.txt

# Remove pre-installed XlsxWriter and install Python dependencies
RUN apt-get update && apt-get install -y libldap2-dev libsasl2-dev
RUN pip uninstall -y XlsxWriter || true
RUN pip install --no-cache-dir --ignore-installed -r requirements.txt
RUN mkdir -p /var/lib/odoo/filestore


# Now copy the rest of the application
COPY . /app

# Make entrypoint script executable
RUN chmod +x /entrypoint.sh

# Set entrypoint
ENTRYPOINT ["/entrypoint.sh"]
