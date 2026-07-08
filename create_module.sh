#!/bin/bash

# Check if a module name was provided
if [ -z "$1" ]; then
    echo "Usage: ./create_module.sh module_name"
    exit 1
fi

MODULE_NAME=$1
ADDONS_PATH=~/odoo/custom_addons

echo "Creating module: $MODULE_NAME"

# Create directories
mkdir -p "$ADDONS_PATH/$MODULE_NAME"/{models,views,security,data,demo,static/src/{css,js,img}}

# Create files
touch "$ADDONS_PATH/$MODULE_NAME/__init__.py"
touch "$ADDONS_PATH/$MODULE_NAME/__manifest__.py"
touch "$ADDONS_PATH/$MODULE_NAME/models/__init__.py"
touch "$ADDONS_PATH/$MODULE_NAME/models/${MODULE_NAME}.py"
touch "$ADDONS_PATH/$MODULE_NAME/views/${MODULE_NAME}_views.xml"
touch "$ADDONS_PATH/$MODULE_NAME/security/ir.model.access.csv"

# __init__.py
cat > "$ADDONS_PATH/$MODULE_NAME/__init__.py" <<EOF
from . import models
EOF

# models/__init__.py
cat > "$ADDONS_PATH/$MODULE_NAME/models/__init__.py" <<EOF
from . import ${MODULE_NAME}
EOF

# __manifest__.py
cat > "$ADDONS_PATH/$MODULE_NAME/__manifest__.py" <<EOF
{
    'name': '$MODULE_NAME',
    'version': '18.0.1.0.0',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'views/${MODULE_NAME}_views.xml',
    ],
    'installable': True,
    'application': True,
}
EOF

echo "✅ Module '$MODULE_NAME' created successfully!"