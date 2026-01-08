{
    'name': "Latvia - Accounting",
    'version': '1.0.0',
    'description': """
Chart of Accounts (COA) Template for Latvia's Accounting.
This module also includes:
* Tax groups,
* Most common Latvian Taxes,
* Fiscal positions,
* Latvian bank list.

author is Allegro IT (visit for more information https://www.allegro.lv)
co-author is Chick.Farm (visit for more information https://www.myacc.cloud)
    """,
    'license': 'LGPL-3',
    'author': "Allegro IT, Chick.Farm",
    'website': "https://allegro.lv",
    'category': 'Accounting/Localizations/Account Charts',
    'depends': [
        'account',
        'base_vat',
    ],
    'data': [
        'data/vat_tax_report.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
}
