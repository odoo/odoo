# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Czech Republic- Accounting Reports',
    'icon': '/account/static/description/l10n.png',
    'countries': ['cz'],
    'version': '1.0',
    'description': """
Accounting reports for Czech Republic
=====================================
    """,
    'category': 'Accounting/Localizations/Reporting',
    'depends': ['l10n_cz', 'account_reports'],
    'data': [
        'data/profit_loss.xml',
        'data/balance_sheet.xml',
    ],
    'auto_install': True,
    'installable': True,
    'license': 'OEEL-1',
}
