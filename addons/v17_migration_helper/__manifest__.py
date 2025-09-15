# File: addons/your_custom_module/__manifest__.py
{
    'name': 'V17 Migration Helper',
    'version': '17.0.1.0.0',
    'category': 'Tools',
    'summary': 'Migration helper for v16 to v17 upgrade',
    'description': 'Migration helper module for upgrading from Odoo v16 to v17. Removes incompatible modules and fixes template references.',
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['base', 'web'],
    'data': [],
    'installable': True,
    'auto_install': True,
    'application': False,
}


