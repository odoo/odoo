# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Switzerland - Accounting Reports',
    'version': '1.1',
    'category': 'Accounting/Localizations/Reporting',
    'description': """
Accounting reports for Switzerland
    """,
    'depends': [
        'l10n_ch', 'account_reports'
    ],
    'data': [
        'data/account_financial_html_report_data.xml',
    ],
    'installable': True,
    'auto_install': ['l10n_ch', 'account_reports'],
    'website': 'https://www.odoo.com/app/accounting',
    'license': 'OEEL-1',
}
