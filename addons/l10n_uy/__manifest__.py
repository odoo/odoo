# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Uruguay - Accounting',
    'website': 'https://www.odoo.com/documentation/saas-16.4/applications/finance/fiscal_localizations.html',
    'icon': '/account/static/description/l10n.png',
    'countries': ['uy'],
    'version': '0.1',
    'author': 'Uruguay l10n Team, Guillem Barba',
    'category': 'Accounting/Localizations/Account Charts',
    'description': """
General Chart of Accounts.
==========================

Provide Templates for Chart of Accounts, Taxes for Uruguay.

""",
    'depends': [
        'account',
    ],
    'data': [
        'data/account_tax_report_data.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'license': 'LGPL-3',
}
