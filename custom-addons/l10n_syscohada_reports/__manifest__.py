# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'OHADA (révisé) - Accounting Reports',
    'icon': '/l10n_syscohada/static/description/icon.jpeg',
    'version': '1.0',
    "author": "Optesis, Odoo",
    'description': """
Accounting reports for OHADA
=================================
    """,
    'category': 'Accounting/Localizations/Reporting',
    'depends': ['l10n_syscohada', 'account_reports'],
    'data': [
        'data/account_financial_html_report_bs_data.xml',
        'data/account_financial_html_report_pl_data.xml',
    ],
    'auto_install': True,
    'license': 'OEEL-1',
}
