{
    'name': 'POS Self Order Loyalty',
    'summary': 'Allows customer identification and loyalty program usage in POS Self Order Mobile/Kiosk.',
    'category': 'Sales/Point Of Sale',
    'depends': ['pos_self_order', 'pos_loyalty'],
    'auto_install': ['pos_self_order', 'pos_loyalty'],
    'data': [
        'security/ir.access.csv',
        'data/mail_template_data.xml',
        'views/loyalty_reward_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'assets': {
        'pos_self_order.assets': [
            'point_of_sale/static/src/app/utils/make_awaitable_dialog.js',
            'pos_self_order_loyalty/static/src/**/*',
            'pos_loyalty/static/src/app/models/**/*',
            ('remove', 'pos_loyalty/static/src/app/models/data_service_options.js'),
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
