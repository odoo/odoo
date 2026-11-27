# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Point of Sale - Loyalty Deposit',
    'category': 'Sales/Point Of Sale',
    'summary': 'Link module between pos_loyalty and pos_deposit',
    'description': """
Deposit lines are refundable amounts, not goods: they neither earn loyalty points
nor receive loyalty discounts. A free product reward still charges the deposit
of its product.
""",
    'depends': ['pos_loyalty', 'pos_deposit'],
    'auto_install': True,
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_loyalty_deposit/static/src/**/*',
        ],
        'web.assets_unit_tests': [
            'pos_loyalty_deposit/static/tests/unit/**/*',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
