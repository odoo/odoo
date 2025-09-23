{
    'name': "Account Peppol Extra Fields",
    'summary': "Adds additional Peppol-specific fields to invoices",
    'description': """
This module introduces Peppol-related fields additional to the ones provided
by the 'account_peppol_advanced_fields' module
    """,
    'author': "Odoo S.A.",
    'category': 'Accounting/Accounting',
    'version': '0.1',
    'depends': ['account_peppol_advanced_fields', 'account_peppol'],
    'data': [
        'views/account_move_views.xml',
        'views/account_tax_views.xml',
    ],
    'auto_install': True,
    'installable': True,
    'license': 'LGPL-3',
}
