# CAMTEL Theme

A custom Odoo theme module for CAMTEL that provides login page customizations.

## Features

- **Warehouse Background Image**: Full-screen warehouse.jpg background image on login page
- **Blue Buttons**: All login buttons are styled with blue background and white text
- **Remove Manage Databases**: The "Manage Databases" link is hidden from the login page
- **Custom Footer**: Changes "Powered by Odoo" to "Powered by Blue" (bold and blue text)

## Installation

1. Place this module in your Odoo addons directory
2. Update your module list in Odoo
3. Install the "CAMTEL Theme" module

## Technical Details

## Technical Details

- Inherits from `web.login_layout` template using XPath expressions
- Applies SCSS styling to buttons and background via asset bundles
- Uses inline styles for footer text customization
- Compatible with Odoo 19.0

## Files

- `__manifest__.py`: Module definition and metadata
- `__init__.py`: Python initialization (empty for theme modules)
- `README.md`: Documentation
- `views/webclient_templates.xml`: Template modifications for login page
- `static/src/scss/login_theme.scss`: SCSS styling for background and buttons
- `static/src/img/warehouse.jpg`: Background image for login page

## Customization

The module can be further customized by modifying:
- `login_theme.scss`: Change button colors, background image, or styling
- `webclient_templates.xml`: Modify which elements are shown/hidden
- `warehouse.jpg`: Replace with a different background image
