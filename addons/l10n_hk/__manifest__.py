# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Hong Kong - Accounting',
<<<<<<< HEAD
    'website': 'https://www.odoo.com/documentation/master/applications/finance/fiscal_localizations/hong_kong.html',
||||||| parent of d9e3022e72f (temp)
    'website': 'https://www.odoo.com/documentation/master/applications/finance/fiscal_localizations.html',
=======
    'website': 'https://www.odoo.com/documentation/saas-16.4/applications/finance/fiscal_localizations.html',
>>>>>>> d9e3022e72f (temp)
    'icon': '/account/static/description/l10n.png',
    'countries': ['hk'],
    'version': '1.0',
    'category': 'Accounting/Localizations/Account Charts',
    'description': ' This is the base module to manage chart of accounting and localization for Hong Kong ',
    'depends': [
        'account_qr_code_emv',
    ],
    'data': [
        'data/account_chart_template_data.xml',
        'views/res_bank_views.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'license': 'LGPL-3',
}
