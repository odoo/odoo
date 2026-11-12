{
    'name': 'POS Glory Cash Machines',
    'category': 'Sales/Point of Sale',
    'summary': 'Integrate your POS with a Glory automatic cash payment device',
    'depends': ['point_of_sale', 'pos_payment_method_glory'],
    'auto_install': True,
    'data': [
        'views/pos_payment_method_views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_glory_cash/static/src/**/*',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
