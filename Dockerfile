# Use the official Odoo 16 image as the base
FROM odoo:16

# Switch to root to install OS packages
USER root

# 1. Install tools and add PGDG repo for matching libpq-dev
RUN apt-get update && \
    apt-get install -y wget gnupg lsb-release postgresql-client && \
    echo "deb http://apt.postgresql.org/pub/repos/apt bullseye-pgdg main" \
      > /etc/apt/sources.list.d/pgdg.list && \
    wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc \
      | apt-key add - && \
    apt-get update

# 2. Install build dependencies (including libpq-dev from PGDG)
RUN apt-get install -y \
      build-essential \
      libssl-dev \
      libffi-dev \
      libpq-dev \
      python3-dev \
      libjpeg62-turbo-dev \
      liblcms2-dev \
      libsasl2-dev \
      libldap2-dev \
      zlib1g-dev && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# 3. Copy your Odoo config, requirements, and custom addons
COPY ./odoo.conf /etc/odoo/odoo.conf
COPY ./requirements.txt /opt/odoo/requirements.txt
COPY ./addons /opt/odoo/addons

WORKDIR /opt/odoo

# 4. Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy entrypoint script into the image and make it executable
COPY ./entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# 6. Switch back to the odoo user
USER odoo

# 7. Expose the Odoo port
EXPOSE 8069

# 8. Use our entrypoint (it will create odoo_user then exec the CMD)
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["odoo", "-c", "/etc/odoo/odoo.conf"]
