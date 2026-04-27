# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Morocco - Accounting Reports',
    'version': '1.1',
    'category': 'Accounting/Localizations/Reporting',
    'description': """
Accounting reports for Morocco.

This module has been built with the help of Caudigef.
    """,
    'depends': [
        'l10n_ma',
        'account_reports',
    ],
    'data': [
        "data/profit_and_loss.xml",
        "data/balance_sheet.xml",
        "data/tax_report.xml",
        "data/l10n_ma_tax_report_template.xml",
        "views/account_payment_views.xml",
        "views/res_partner_views.xml",
        "views/account_move_views.xml",
        "wizard/account_payment_register_views.xml",
    ],
    'installable': True,
    'auto_install': [
        'l10n_ma',
        'account_reports',
    ],
    'website': 'https://www.odoo.com/app/accounting',
    'license': 'OEEL-1',
}
