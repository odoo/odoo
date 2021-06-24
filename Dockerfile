# TAG		odoo/crm
# -----------------------------------------------------------------------------
# BUILDING IMAGE
FROM		python:3.9.4-alpine as builder
MAINTAINER	Manuel F Martinez <manuel@wishpond.com>

		# Set working directory
WORKDIR		/odoo

		# Application requirements
ADD		./ .

		# Python application and dependencies
RUN		apk add --no-cache build-base linux-headers libffi-dev libxml2-dev libxslt-dev openldap-dev openssl-dev postgresql-dev jpeg-dev && \
		pip install --prefix=/build -r requirements.txt /odoo && \
		# Copy without replacing the base addons \
		cp -r addons/* /build/lib/python3.9/site-packages/odoo/addons/

# -----------------------------------------------------------------------------
# DEPLOYMENT IMAGE
FROM		python:3.9.4-alpine
MAINTAINER	Manuel F Martinez <manuel@wishpond.com>

		# Install dependencies
RUN		apk add --no-cache postgresql-libs wkhtmltopdf

		# Copy the built dependencies
COPY		--from=builder /build /usr/local

		# Do not run as root!
RUN 		addgroup -S odoo && \
		adduser -S -D -G odoo odoo && \
		mkdir -p /mnt/extra-addons /var/lib/odoo /etc/odoo && \
		chown -R odoo:odoo /mnt/extra-addons /var/lib/odoo /home/odoo /etc/odoo

		# User volumes
VOLUME		["/var/lib/odoo", "/mnt/extra-addons"]

		# Runtime user
USER 		odoo

		# Binding port tags
EXPOSE		8069 8071 8072

		# Current version as of Jun 2021
ENV		ODOO_VERSION=14.0

		# Make it easy for k8s to see the output logs
ENV		PYTHONUNBUFFERED=0

		# Default config file
ENV		ODOO_RC=/etc/odoo/odoo.conf

		# Runtime application
CMD		["odoo"]
