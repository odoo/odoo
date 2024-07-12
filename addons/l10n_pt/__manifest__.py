# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Portugal - Accounting',
    'website': 'https://www.odoo.com/documentation/master/applications/finance/fiscal_localizations.html',
    'icon': '/account/static/description/l10n.png',
    'countries': ['pt'],
    'version': '1.0',
    'author': 'Odoo',
    'category': 'Accounting/Localizations/Account Charts',
    'description': 'Portugal - Accounting',
    'depends': [
        'base',
        'account',
        'base_vat',
    ],
    'auto_install': ['account'],
    'data': [
        'data/account_tax_report.xml',
        'security/ir.model.access.csv',
        'security/l10n_pt_security.xml',
        'views/account_move_views.xml',
        'views/account_tax_views.xml',
        'views/l10n_pt_at_series_views.xml',
        'views/report_invoice.xml',
        'views/report_template.xml',
        'views/res_config_settings_views.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
        'demo/ir_config_parameter_data.xml',
    ],
    'license': 'LGPL-3',
}
