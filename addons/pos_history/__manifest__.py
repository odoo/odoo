# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Point of Sale History',
    'category': 'Accounting/Localizations/Point of Sale',
    'summary': 'Tracks deleted POS orders & orderlines, providing better auditability and control',
    'depends': ['point_of_sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/pos_order_view.xml',
        'views/res_config_settings_view.xml',
    ],
    'post_init_hook': 'pos_history_post_init',
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_history/static/src/**/*',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
