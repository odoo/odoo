{
    'name': 'POS Mollie',
    'category': 'Sales/Point of Sale',
    'sequence': 6,
    'summary': 'Integrate your POS with a Mollie payment terminal',
    'depends': ['point_of_sale', 'payment_mollie'],
    'data': [
        'views/pos_payment_method_views.xml',
    ],
    'assets': {
        'point_of_sale.payment_terminals': [
            'pos_mollie/static/src/**/*',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
