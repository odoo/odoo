# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Algeria - Accounting Reports',
    'countries': ['dz'],
    'version': '0.1',
    'description': """
Accounting reports for Algeria
================================
    """,
    'category': 'Accounting/Localizations/Reporting',
    'depends': ['l10n_dz', 'account_reports'],
    'data': [
        'data/balance_sheet.xml',
        'data/profit_loss.xml',
    ],
    'auto_install': ['l10n_dz', 'account_reports'],
    'installable': True,
    'license': 'OEEL-1',
}
