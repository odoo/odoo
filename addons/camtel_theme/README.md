# CAMTEL Theme

A custom Odoo theme module for CAMTEL that provides login page customizations.

## Features

- **Blue Buttons**: All login buttons are styled with blue background and white text
- **Remove Manage Databases**: The "Manage Databases" link is hidden from the login page
- **Custom Footer**: Changes "Powered by Odoo" to "Powered by Blue"

## Installation

1. Place this module in your Odoo addons directory
2. Update your module list in Odoo
3. Install the "CAMTEL Theme" module

## Technical Details

- Inherits from `web.login_layout` template
- Uses XPath expressions to modify the login page structure
- Applies SCSS styling to buttons via asset bundles
- Compatible with Odoo 19.0

## Files

- `__manifest__.py`: Module definition and metadata
- `__init__.py`: Python initialization (empty for theme modules)
- `views/webclient_templates.xml`: Template modifications for login page
- `static/src/scss/login_theme.scss`: SCSS styling for blue buttons

## Customization

The module can be further customized by modifying:
- `login_theme.scss`: Change button colors and styling
- `webclient_templates.xml`: Modify which elements are shown/hidden
