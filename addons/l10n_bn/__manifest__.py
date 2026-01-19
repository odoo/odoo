# -*- coding: utf-8 -*-
{
    'name': "Brunei Darussalam - Accounting",
    'website': "https://nanas.systems",
    'icon': '/account/static/description/l10n.png',
    'countries': ['bn'],
    'author': 'Nanas Systems Sdn. Bhd.',
    'version': '0.1',
    'category': 'Accounting/Localizations/Account Charts',
    'license': 'LGPL-3',
    'summary': """
Brunei Accounting Chart and Localisation.

    """,

    'description': """
This module add the following:
 - Add Company / Business Registration Number to report layout
 - Add generic chart of accounts
 - Add bank details

    """,
    'depends': ['account'],
    'auto_install': ['account'],
    'data': [
        'data/template/res.bank.csv',
        'views/report_layout.xml',
    ],
}
