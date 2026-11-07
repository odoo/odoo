# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'POS Self Order - Deposit',
    'category': 'Sales/Point Of Sale',
    'summary': 'Add deposit lines to the self order cart',
    'depends': ['pos_self_order', 'pos_deposit'],
    'auto_install': True,
    'assets': {
        'pos_self_order.assets': [
            'pos_deposit/static/src/app/models/**/*',
            'pos_self_order_deposit/static/src/app/**/*',
        ],
        'web.assets_unit_tests': [
            'pos_self_order_deposit/static/tests/unit/**/*',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
