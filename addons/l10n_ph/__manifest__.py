# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Philippines - Accounting',
    'icon': '/account/static/description/l10n.png',
    'countries': ['ph'],
    'summary': "This is the module to manage the accounting chart for The Philippines.",
    'category': 'Accounting/Localizations/Account Charts',
    'version': '1.1',
    'author': 'Odoo PS',
    'website': 'https://www.odoo.com/documentation/master/applications/finance/fiscal_localizations/philippines.html',
    'depends': [
        'account',
        'base_vat',
    ],
    'auto_install': ['account'],
    'data': [
        'data/account_account_tag_data.xml',
        'data/account_tax_report_data.xml',
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
