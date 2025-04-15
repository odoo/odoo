# Use an official Odoo image as a base
FROM odoo:16

# Set environment variables
ENV HOME /opt/odoo

# Set the working directory to /opt/odoo
WORKDIR /opt/odoo

# Copy the configuration file
COPY ./odoo.conf /etc/odoo.conf

# Copy your custom modules to the addons directory
COPY ./addons /opt/odoo/addons

# Install dependencies (ensure you have a requirements.txt if necessary)
RUN pip install -r /opt/odoo/requirements.txt

# Expose port 8069 (the default Odoo port)
EXPOSE 8069

# Start Odoo
CMD ["odoo", "-c", "/etc/odoo.conf"]
