# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Kazakhstan - Accounting Reports',
    'countries': ['kz'],
    'version': '1.0',
    'description': """
Accounting reports for Kazakhstan
Contains Balance sheet, Profit and Loss reports
    """,
    'category': 'Accounting/Localizations/Reporting',
    'depends': ['l10n_kz', 'account_reports'],
    'data': [
        'data/balance_sheet.xml',
        'data/profit_loss.xml',
    ],
    'auto_install': True,
    'installable': True,
    'license': 'OEEL-1',
}
