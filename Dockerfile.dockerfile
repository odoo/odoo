# Use the official Odoo image as a base image
FROM odoo:16

# Copy your custom configuration file and modules
COPY ./odoo.conf /etc/odoo/odoo.conf
COPY ./addons /mnt/extra-addons

# Set environment variables if needed
ENV DB_HOST=postgres
ENV DB_PORT=5432

# Set the entrypoint and command to start Odoo 
CMD ["odoo", "--config", "/etc/odoo/odoo.conf"]
