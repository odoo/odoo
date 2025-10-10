# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'POS Self Order - Event',
    'category': 'Sales/Point Of Sale',
    'version': '1.0',
    'summary': 'Link module between PoS Self Order and PoS Event',
    'depends': ['pos_self_order', 'pos_event'],
    'installable': True,
    'auto_install': True,
    'assets': {
        'pos_self_order.assets': [
            'pos_self_order_event/static/src/**/*',
            'pos_event/static/src/app/models/**/*',
            'pos_event/static/src/app/utils/**/*',
        ],
    },
    'author': 'Odoo IN Pvt Ltd',
    'license': 'LGPL-3',
}
