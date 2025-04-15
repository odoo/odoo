# Use an official Odoo image as a base
FROM odoo:16

# Set environment variables
ENV HOME /opt/odoo

# Set the working directory to /opt/odoo
WORKDIR /opt/odoo

# Copy the Odoo configuration file
COPY ./odoo.conf /etc/odoo.conf

# Copy your custom modules to the addons directory
COPY ./addons /opt/odoo/addons

# Install dependencies from requirements.txt (if it exists)
COPY ./requirements.txt /opt/odoo/requirements.txt
RUN pip3 install -r /opt/odoo/requirements.txt

# Expose the default Odoo port
EXPOSE 8069

# Start Odoo with the provided configuration
CMD ["odoo", "-c", "/etc/odoo.conf"]
