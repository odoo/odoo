# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Philippines - Accounting',
    'icon': '/account/static/description/l10n.png',
    'countries': ['ph'],
    'summary': """
        This is the module to manage the accounting chart for The Philippines.
    """,
    'category': 'Accounting/Localizations/Account Charts',
    'version': '1.0',
    'author': 'Odoo PS',
<<<<<<< HEAD
    'website': 'https://www.odoo.com/documentation/master/applications/finance/fiscal_localizations/philippines.html',
||||||| parent of d9e3022e72f (temp)
    'website': 'https://www.odoo.com/documentation/master/applications/finance/fiscal_localizations.html',
=======
    'website': 'https://www.odoo.com/documentation/saas-16.4/applications/finance/fiscal_localizations.html',
>>>>>>> d9e3022e72f (temp)
    'depends': [
        'account',
        'base_vat',
    ],
    'data': [
        'wizard/generate_2307_wizard_views.xml',
        'views/account_move_views.xml',
        'views/account_payment_views.xml',
        'views/account_tax_views.xml',
        'views/res_partner_views.xml',
        'security/ir.model.access.csv',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'license': 'LGPL-3',
}
