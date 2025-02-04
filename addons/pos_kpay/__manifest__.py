{
    'name': 'POS KPay',
    'version': '1.0',
    'category': 'Sales/Point of Sale',
    'sequence': 6,
    'summary': 'Integrate your POS with the KPay terminal',
    'data': [
        'views/pos_payment_method_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'depends': ['point_of_sale', 'payment'],
    'installable': True,
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_kpay/static/**/*',
        ],
    },
    'license': 'LGPL-3',
}
