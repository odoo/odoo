# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Kenya - Accounting Reports',
    'version': '1.0',
    'description': """
Accounting reports for Kenya
============================

    """,
    'category': 'Accounting/Localizations/Reporting',
    'depends': ['l10n_ke', 'account_reports'],
    'data': [
        'data/balance_sheet.xml',
        'data/profit_loss.xml',
    ],
    'auto_install': True,
    'installable': True,
    'post_init_hook': '_l10n_ke_reports_post_init',
    'license': 'OEEL-1',
}
