# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Portugal',
    'website': 'https://www.odoo.com/documentation/master/applications/finance/fiscal_localizations.html',
    'icon': '/account/static/description/l10n.png',
    'countries': ['pt'],
    'version': '1.0',
    'author': 'Odoo',
    'category': 'Accounting/Localizations/Account Charts',
    'description': 'Portugal - Accounting',
    'depends': [
        'base',
    ],
    'data': [
        'views/l10n_pt_tax_authority_series_views.xml',
        'security/ir.model.access.csv',
    ],
    'demo': [
        'demo/demo_company.xml',
        'demo/demo_data.xml',
        'demo/ir_config_parameter_data.xml',
    ],
    'license': 'LGPL-3',
}
