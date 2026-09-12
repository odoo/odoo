# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Portugal - Point of Sale',
    'description': """Point of Sale module for Portugal which allows hash and QR code on POS orders""",
    'category': 'Accounting/Localizations/Point of Sale',
    'depends': [
        'l10n_pt_certification',
        'point_of_sale',
    ],
    'data': [
        'views/pos_config_views.xml',
        'views/pos_order_views.xml',
        'views/pos_payment_method_views.xml',
        'views/product_views.xml',
        'views/res_config_settings_views.xml',
        'report/l10n_pt_pos_hash_integrity_templates.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'l10n_pt_pos/static/src/**/*',
        ],
    },
    'license': 'LGPL-3',
    'auto_install': True,
}
