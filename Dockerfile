# Base image
FROM python:3.8-slim

# Environment variables
ENV ODOO_VERSION=17.0 \
    ODOO_USER=odoo \
    ODOO_HOME=/opt/odoo \
    ODOO_CONF=/etc/odoo.conf \
    ODOO_LOG=/var/log/odoo \
    PG_VERSION=14

# Install dependencies
RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    libxml2-dev \
    libxslt1-dev \
    zlib1g-dev \
    libsasl2-dev \
    libldap2-dev \
    libjpeg-dev \
    libpq-dev \
    libffi-dev \
    libssl-dev \
    wkhtmltopdf \
    npm && \
    npm install -g less less-plugin-clean-css

# Copy Odoo source code to the image
COPY . $ODOO_HOME

# Set up Python virtual environment
RUN python3 -m venv $ODOO_HOME/venv
RUN $ODOO_HOME/venv/bin/pip install -r $ODOO_HOME/requirements.txt

# Create Odoo configuration file
RUN mkdir -p $ODOO_LOG && touch $ODOO_CONF

# Copy the configuration file template
COPY odoo.conf $ODOO_CONF

# Set permissions
RUN chown -R $ODOO_USER:$ODOO_USER $ODOO_HOME

# Add entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Switch to Odoo user
USER $ODOO_USER

# Expose Odoo port
EXPOSE 8069

# Run Odoo
# CMD ["sh", "-c", "$ODOO_HOME/venv/bin/python $ODOO_HOME/odoo-bin -c $ODOO_CONF"]
ENTRYPOINT ["/entrypoint.sh"]
