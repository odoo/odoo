# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Portugal - Sale',
    'description': """Sale module for Portugal which allows hash and QR code on sale orders""",
    'category': 'Accounting/Localizations/Stock',
    'depends': [
        'l10n_pt_certification',
        'sale',
    ],
    'data': [
        'views/sale_order_views.xml',
        'views/res_config_settings_views.xml',
        'report/ir_actions_report_templates.xml',
        'report/l10n_pt_sale_hash_integrity_templates.xml',
    ],
    'auto_install': True,
    'license': 'LGPL-3',
}
