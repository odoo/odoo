# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Account Winbooks Import",
    'summary': """Import Data From Winbooks""",
    'description': """
Import Data From Winbooks
    """,
    'category': 'Accounting/Accounting',
    'depends': ['account_accountant', 'base_vat', 'account_base_import'],
    'external_dependencies': {'python': ['dbfread']},
    'data': [
        'security/ir.model.access.csv',
        'wizard/import_wizard_views.xml',
    ],
    'license': 'OEEL-1',
    'assets': {
        'web.assets_backend': [
            'account_winbooks_import/static/src/xml/**/*',
        ],
    },
}
