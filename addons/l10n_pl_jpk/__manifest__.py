# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Poland - JPK_VAT Community',
    'version': '1.0',
    'description': """
        All the fields needed for the JPK_VAT Export in Poland are available in Community
    """,
    'category': 'Accounting/Localizations/Reporting',
    'depends': [
        'l10n_pl',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/l10n_pl_tax_office.csv',
        'views/account_move_views.xml',
        'views/product_views.xml',
        'views/report_invoice.xml',
        'views/res_config_settings_views.xml',
        'views/res_partner_views.xml',
    ],
    'auto_install': True,
    'installable': True,
    'website': 'https://www.odoo.com/app/accounting',
    'license': 'LGPL-3',
}
