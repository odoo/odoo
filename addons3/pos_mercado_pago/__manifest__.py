{
    'name': 'POS Mercado Pago',
    'version': '1.0',
    'category': 'Sales/Point of Sale',
    'sequence': 6,
    'summary': 'Integrate your POS with the Mercado Pago Smart Point terminal',
    'data': [
        'views/pos_payment_method_views.xml',
    ],
    'depends': ['point_of_sale'],
    'installable': True,
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_mercado_pago/static/**/*',
        ],
    },
    'license': 'LGPL-3',
}
