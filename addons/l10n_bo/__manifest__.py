# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Bolivia - Accounting',
    'website': 'https://www.odoo.com/documentation/master/applications/finance/fiscal_localizations.html',
    'icon': '/account/static/description/l10n.png',
    'countries': ['bo'],
    'version': '2.0',
    'description': """
Bolivian accounting chart and tax localization.

Plan contable boliviano e impuestos de acuerdo a disposiciones vigentes

    """,
    'author': 'Odoo / Kyohei Ltda',
    'category': 'Accounting/Localizations/Account Charts',
    'depends': [
        'account',
        'account_tax_python'
    ],
    'auto_install': ['account'],
    'data': [
        'data/account.account.tag',
        'data/contact_bank_data.xml'
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'license': 'LGPL-3',
}
