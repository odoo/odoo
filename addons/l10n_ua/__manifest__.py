# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Ukraine - Accounting',
    'icon': '/account/static/description/l10n.png',
    'countries': ['ua'],
    'author': 'ERP Ukraine (https://erp.co.ua)',
    'website': 'https://www.odoo.com/documentation/latest/applications/finance/fiscal_localizations.html',
    'version': '1.4',
    'description': """
Ukraine - Chart of accounts.
============================
    """,
    'category': 'Accounting/Localizations/Account Charts',
    'depends': [
        'account',
    ],
    'auto_install': ['account'],
    'data': [
        'data/account_account_tag_data.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'license': 'LGPL-3',
}
