#!/bin/bash

clear
printf "\033c"
# Activate the virtual environment
echo "Activating virtual environment..."
source ~/dev/venv_odoo/bin/activate

# Kill existing Odoo processes
# echo "Killing existing Odoo processes..."
# ps aux | grep odoo | grep -v grep | awk '{print $2}' | xargs kill -9
# ps aux | grep '[o]doo' | awk '{print $2}' | xargs kill -9

# Delete .pyc files
echo "Deleting .pyc files..."
find . -name "*.pyc" -delete

# Delete __pycache__ directories
echo "Deleting __pycache__ directories..."
find . -name "__pycache__" -type d -exec rm -r {} +

# Start the Odoo server and show logs
echo "Starting Odoo server..."
./odoo-bin -c odoo.conf -u all