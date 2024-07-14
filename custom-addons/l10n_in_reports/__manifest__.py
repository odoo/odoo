# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Indian - Accounting Reports',
    'countries': ['in'],
    'version': '1.1',
    'description': """
Accounting reports for India
================================
    """,
    'category': 'Accounting/Localizations/Reporting',
    'depends': ['l10n_in', 'account_reports'],
    'data': [
        'data/account_financial_html_report_gstr1.xml',
        'data/account_financial_html_report_gstr3b.xml',
    ],
    'auto_install': ['l10n_in', 'account_reports'],
    'installable': True,
    'license': 'OEEL-1',
}
