# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Estonia - Accounting',
<<<<<<< saas-17.4
    'website': 'https://www.odoo.com/documentation/master/applications/finance/fiscal_localizations.html',
    'version': '1.1',
||||||| 74373629bc5bac5a8aa9a061020a6588f79ff766
    'website': 'https://www.odoo.com/documentation/saas-17.2/applications/finance/fiscal_localizations.html',
    'version': '1.1',
=======
    'website': 'https://www.odoo.com/documentation/saas-17.2/applications/finance/fiscal_localizations.html',
    'version': '1.2',
>>>>>>> 7987ae47842ce6b30709f9d16cc8d8f5e05f2516
    'icon': '/account/static/description/l10n.png',
    'countries': ['ee'],
    'category': 'Accounting/Localizations/Account Charts',
    'description': """
This is the base module to manage the accounting chart for Estonia in Odoo.
    """,
    'author': 'Odoo SA',
    'depends': [
        'account',
    ],
    'auto_install': ['account'],
    'data': [
        'data/account_tax_report_data.xml',
        'views/account_tax_form.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'license': 'LGPL-3',
}
