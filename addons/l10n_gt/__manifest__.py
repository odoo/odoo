# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Guatemala - Accounting',
    'icon': '/account/static/description/l10n.png',
    'countries': ['gt'],
    'version': '3.0',
    'category': 'Accounting/Localizations/Account Charts',
    'description': """
This is the base module to manage the accounting chart for Guatemala.
=====================================================================

Agrega una nomenclatura contable para Guatemala. También icluye impuestos y
la moneda del Quetzal. -- Adds accounting chart for Guatemala. It also includes
taxes and the Quetzal currency.""",
    'author': 'José Rodrigo Fernández Menegazzo',
    'website': 'https://www.odoo.com/documentation/latest/applications/finance/fiscal_localizations.html',
    'depends': [
        'base_address_extended',
        'account',
        'account_tax_python',
        'l10n_account_withholding_tax',
    ],
    'auto_install': ['account'],
    'data': [
        'data/res.city.csv',
        'views/product_views.xml',
        'views/res_company_views.xml',
        'views/res_partner_views.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'license': 'LGPL-3',
}
