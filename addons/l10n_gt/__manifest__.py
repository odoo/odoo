# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Guatemala - Accounting',
    'icon': '/account/static/description/l10n.png',
    'countries': ['gt'],
    'version': '3.1',
    'category': 'Accounting/Localizations/Account Charts',
    'description': """
This is the base module to manage the accounting chart for Guatemala.
=====================================================================

Agrega una nomenclatura contable para Guatemala. También icluye impuestos y
la moneda del Quetzal. -- Adds accounting chart for Guatemala. It also includes
taxes and the Quetzal currency.""",
    'author': 'José Rodrigo Fernández Menegazzo',
    'website': 'https://www.odoo.com/documentation/master/applications/finance/fiscal_localizations.html',
    'depends': [
        'account_tax_python',
        'l10n_latam_base',
        'account',
    ],
    'auto_install': ['account'],
    'data': [
        'data/l10n_gt_identification_type_data.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
        'demo/demo_partner.xml',
    ],
    'license': 'LGPL-3',
}
