# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Portugal - Point of Sale',
    'version': '1.0',
    'countries': ['pt'],
    'description': """Point of Sale module for Portugal which allows hash and QR code on POS orders""",
    'category': 'Accounting/Localizations/Point of Sale',
    'depends': [
        'point_of_sale',
        'l10n_pt',
    ],
    'auto_install': [
        'point_of_sale',
        'l10n_pt',
    ],
    'data': [
        'views/pos_config_views.xml',
        'views/pos_order_views.xml',
        'views/res_config_settings_views.xml',
        'report/l10n_pt_pos_hash_integrity_templates.xml',
    ],
    'demo': [
        'demo/demo_data.xml',
        'demo/product_demo.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'l10n_pt_pos/static/src/app/**/*',
        ],
    },
    'license': 'LGPL-3',
}
