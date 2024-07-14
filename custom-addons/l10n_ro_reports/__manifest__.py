# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Romania - Accounting Reports',
    'countries': ['ro'],
    'version': '1.0',
    'category': 'Accounting/Localizations/Reporting',
    'description': """
Accounting reports for Romania
    """,
    'depends': [
        'l10n_ro', 'account_reports'
    ],
    'data': [
        "data/balance_sheet_short.xml",
        "data/balance_sheet_internat.xml",
        "data/profit_loss_micro.xml",
        "data/profit_loss_smle.xml",
        "data/profit_loss_internat.xml",
    ],
    'installable': True,
    'auto_install': True,
    'website': 'https://www.odoo.com/app/accounting',
    'license': 'OEEL-1',
}
