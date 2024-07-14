# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Bolivia - Accounting Reports',
    'countries': ['bo'],
    'version': '1.0',
    'category': 'Accounting/Localizations/Reporting',
    'description': """
Base module for Bolivian reports
    """,
    'depends': [
        'l10n_bo',
        'account_reports',
    ],
    'data': [
        'data/profit_loss.xml',
        'data/balance_sheet.xml',
    ],
    'auto_install': True,
    'installable': True,
    'license': 'OEEL-1',
}
