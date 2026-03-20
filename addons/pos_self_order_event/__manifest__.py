# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'POS Self Order - Event',
    'category': 'Sales/Point Of Sale',
    'summary': 'Link module between PoS Self Order and PoS Event',
    'depends': ['pos_self_order', 'pos_event'],
    'auto_install': True,
    'assets': {
        'pos_self_order.assets': [
            'pos_self_order_event/static/src/**/*',
            'pos_event/static/src/app/models/**/*',
            'pos_event/static/src/app/utils/**/*',
        ],
        'web.assets_unit_tests': [
            'pos_self_order_event/static/tests/unit/**/*',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
