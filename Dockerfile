FROM odoo:16

# Switch to root to install dependencies
USER root

RUN apt-get update && apt-get install -y \
    build-essential \
    libssl-dev \
    libffi-dev \
    libpq-dev \
    python3-dev \
    libjpeg8-dev \
    liblcms2-dev \
    libsasl2-dev \
    libldap2-dev \
    zlib1g-dev \
 && apt-get clean && rm -rf /var/lib/apt/lists/*

# Switch back to odoo user
USER odoo

COPY ./odoo.conf /etc/odoo/odoo.conf
COPY ./requirements.txt /opt/odoo/requirements.txt
COPY ./addons /opt/odoo/addons
WORKDIR /opt/odoo
RUN pip install -r /opt/odoo/requirements.txt

# Back to root to add entrypoint
USER root
COPY ./entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Entrypoint that will handle user creation and Odoo startup
ENTRYPOINT ["/entrypoint.sh"]
