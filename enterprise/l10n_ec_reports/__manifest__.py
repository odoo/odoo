# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Ecuadorian Accounting Reports',
    'version': '2.0',
    'description': '''
Accounting reports for Ecuador
==============================
* Adds Balance Sheet report adapted for Ecuador
* Adds Profit and Loss report adapted for Ecuador
    ''',
    'author': 'TRESCLOUD',
    'category': 'Accounting/Localizations/Reporting',
    'license': 'OPL-1',
    'depends': [
        'l10n_ec',
        'account_reports',
        ],
    'data': [
        'data/account_financial_html_report_data.xml',
    ],
    'auto_install': True,
    'installable': True,
}
