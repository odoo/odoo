# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Norway - Accounting Reports',
    'countries': ['no'],
    'version': '1.1',
    'description': """
Accounting reports for Norway
================================

    """,
    'category': 'Accounting/Localizations/Reporting',
    'depends': ['l10n_no', 'account_reports'],
    'data': [
        'data/profit_loss.xml',
        'data/balance_sheet.xml',
        'data/tax_report.xml',
        'data/tax_report_export.xml',
    ],
    'auto_install': ['l10n_no', 'account_reports'],
    'installable': True,
    'license': 'OEEL-1',
}
