# -*- encoding: utf-8 -*-
# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Pakistan - Accounting Reports',
    'countries': ['pk'],
    'version': '1.0',
    'description': """
Accounting reports for Pakistan
    """,
    'category': 'Accounting/Localizations/Reporting',
    'depends': ['l10n_pk', 'account_reports'],
    'data': [
        'data/balance_sheet.xml',
        'data/profit_and_loss.xml',
        'data/report_actions.xml',
    ],
    'auto_install': ['l10n_pk', 'account_reports'],
    'installable': True,
    'license': 'OEEL-1',
}
