#!/bin/bash

# Function to initialize Odoo
initialize_odoo() {
    echo "Initializing Odoo..."
    ./odoo-bin -c $ODOO_CONF -d odoo --init=all
}

# Run initialization only on first start
if [ ! -f /.initialized ]; then
    touch /.initialized
    initialize_odoo
fi

# Start Odoo
echo "Starting Odoo..."
exec su-exec $ODOO_USER $ODOO_HOME/venv/bin/python $ODOO_HOME/odoo-bin -c $ODOO_CONF
