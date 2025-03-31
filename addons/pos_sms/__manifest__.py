{
    'name': 'POS - SMS',
    'category': 'Send sms to customer for order confirmation',
    'description': """This module integrates the Point of Sale with SMS""",
    'depends': ['point_of_sale', 'sms'],
    'data': [
        'data/sms_data.xml',
        'views/res_config_settings_views.xml',
        'data/point_of_sale_data.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_sms/static/src/**/*',
        ],
    },
    'license': 'LGPL-3',
    'auto_install': True
}
