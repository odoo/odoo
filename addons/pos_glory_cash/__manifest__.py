{
    'name': 'PoS Glory bridge',
    'category': 'Sales/Point of Sale',
    'summary': 'UI integration in the PoS for Glory cash machines',
    'depends': ['point_of_sale', 'pos_payment_method_glory'],
    'auto_install': True,
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_glory_cash/static/src/**/*',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
