# -*- encoding: utf-8 -*-

{
    "name": "Tunisia - Accounting",
    "version": "1.0",
    "category": 'Accounting/Localizations/Account Charts',
    "description": """
This is the module to manage the accounting chart for Tunisia in Odoo.
=======================================================================
""",
    'depends': [
        'account',
    ],
    'data': [
        'data/tax_report.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'license': 'LGPL-3',
}
