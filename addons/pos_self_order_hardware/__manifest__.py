# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'PoS Hardware API integration',
    'version': '1.0.0',
    'category': 'Sales/Point of Sale',
    'sequence': 40,
    'summary': 'Allows the use of various hardware, such as an LED screen.',
    'depends': ['pos_self_order'],
    'uninstall_hook': 'uninstall_hook',
    'data': [
        'views/res_config_settings_views.xml',
    ],
    'demo': [],
    'installable': True,
    'application': False,
    'assets': {
        "pos_self_order.assets": [
            'pos_self_order_hardware/static/src/**/*.js',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
