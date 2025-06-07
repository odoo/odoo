# -*- encoding: utf-8 -*-

{
    "name": "Tunisia - Accounting",
    "version": "1.0",
    'icon': '/account/static/description/l10n.png',
    'countries': ['tn'],
    "category": 'Accounting/Localizations/Account Charts',
    "description": """
This is the module to manage the accounting chart for Tunisia in Odoo.
=======================================================================
""",
    'depends': [
        'account',
    ],
    'auto_install': ['account'],
    'data': [
        'data/tax_report.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'license': 'LGPL-3',
}
