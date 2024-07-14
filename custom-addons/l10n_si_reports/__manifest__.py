# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Slovenia - Accounting Reports',
    'countries': ['si'],
    'version': '1.0',
    'category': 'Accounting/Localizations/Reporting',
    'description': """ Base module for Slovenian reports """,
    'depends': [
        'l10n_si',
        'account_reports',
    ],
    'data': [
        'data/balance_sheet.xml',
        'data/profit_loss.xml',
    ],
    'auto_install': True,
    'installable': True,
    'license': 'OEEL-1',
}
