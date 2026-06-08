# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'POS Self Order SMS',
    'category': 'Sales/Point Of Sale',
    'description': """Integrates POS Self Order with SMS to send customers order confirmation via SMS.""",
    'depends': ['pos_self_order', 'pos_sms'],
    'data': [
        'data/preset_data.xml',
        'views/pos_preset_views.xml',
    ],
    'assets': {
        'pos_self_order.assets': [
            'pos_self_order_sms/static/src/**/*',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
    'auto_install': True,
}
