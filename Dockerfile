# =============================================================================
# Multi-Stage Dockerfile for Odoo 19 with Custom Modules
# Optimized for low-resource VPS (1GB RAM, 1 CPU)
# =============================================================================

ARG BUILD_DATE
ARG VCS_REF

# =============================================================================
# Stage 1: Builder - Python dependencies only
# =============================================================================
FROM python:3.12-slim-bookworm AS builder

# Install build dependencies (temporary, will be removed in final stage)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libldap2-dev \
    libsasl2-dev \
    libssl-dev \
    libffi-dev \
    libjpeg-dev \
    libpng-dev \
    zlib1g-dev \
    libxml2-dev \
    libxslt1-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment in builder
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" \
    VIRTUAL_ENV="/opt/venv"

# Copy requirements ONLY (for better layer caching on code changes)
COPY requirements.txt /tmp/

# Install Python packages with no cache
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r /tmp/requirements.txt

# -----------------------------------------------------------------------------
# Stage 2: Production - Minimal runtime image
# -----------------------------------------------------------------------------
FROM python:3.12-slim-bookworm AS production

# Build arguments from stage 1
ARG BUILD_DATE
ARG VCS_REF

# Labels for GHCR and image tracking
LABEL org.opencontainers.image.created="${BUILD_DATE}"
LABEL org.opencontainers.image.revision="${VCS_REF}"
LABEL org.opencontainers.image.source="https://github.com/laxya911/custom-odoo"
LABEL org.opencontainers.image.description="Odoo 19 with Uber Eats Integration"
LABEL org.opencontainers.image.licenses="LGPL-3.0"
LABEL maintainer="Your Organization"

# Runtime dependencies only (minimal)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libldap-2.5-0 \
    libsasl2-2 \
    libssl3 \
    libjpeg62-turbo \
    libpng16-16 \
    libxml2 \
    libxslt1.1 \
    fonts-dejavu-core \
    fonts-noto-core \
    # For wkhtmltopdf PDF generation
    wkhtmltopdf \
    xfonts-75dpi \
    xfonts-base \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for security
RUN useradd -m -d /opt/odoo -s /sbin/nologin odoo

# Set working directory
WORKDIR /opt/odoo

# Copy virtual environment from builder (much smaller than rebuild)
COPY --from=builder --chown=odoo:odoo /opt/venv /opt/venv

# Copy Odoo core (ensure proper permissions)
COPY --chown=odoo:odoo odoo ./odoo
COPY --chown=odoo:odoo odoo-bin ./

# Copy official odoo addons
COPY --chown=odoo:odoo addons ./addons

# Copy custom addons to SEPARATE directory
COPY --chown=odoo:odoo custom_addons ./custom_addons

# Copy setup configuration
COPY --chown=odoo:odoo setup.py setup.cfg ./

# Create required directories with proper permissions
RUN mkdir -p /var/lib/odoo \
    /opt/odoo/custom_addons \
    /opt/odoo/extra-addons \   
    /opt/odoo/logs \
    /tmp/odoo-sessions \
    /tmp/odoo-session-config \
    && chown -R odoo:odoo /var/lib/odoo /opt/odoo /tmp/odoo-sessions /tmp/odoo-session-config \
    && chmod 755 /var/lib/odoo /opt/odoo /tmp/odoo-sessions /tmp/odoo-session-config

# Environment variables
ENV PATH="/opt/venv/bin:$PATH" \
    VIRTUAL_ENV="/opt/venv" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    ODOO_RC=/etc/odoo/odoo.conf \
    ODOO_DATA_DIR=/var/lib/odoo \
    WERKZEUG_RUN_MAIN=true

# Expose Odoo port
EXPOSE 8069 8072

# Switch to non-root user before running
USER odoo

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8069/web/health')" || exit 1

# Default command
ENTRYPOINT ["python", "/opt/odoo/odoo-bin"]
CMD ["--help"]
