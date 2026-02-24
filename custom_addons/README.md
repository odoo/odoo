# Custom Addons Directory

Place your third-party and custom Odoo modules here.

## Structure

Each module should be its own directory:

```
custom_addons/
├── my_custom_module/
│   ├── __init__.py
│   ├── __manifest__.py
│   ├── models/
│   ├── views/
│   ├── security/
│   └── ...
├── another_module/
│   └── ...
└── README.md
```

## Adding a Module

1. Copy or clone the module folder into this directory
2. Ensure the module has a valid `__manifest__.py` with the correct Odoo version
3. Restart Odoo and update the apps list: Settings > Apps > Update Apps List
4. Search for and install the module

## Version Compatibility

This installation targets **Odoo 18 Community Edition**. Ensure all custom modules
are compatible with Odoo 18 before installing them.
