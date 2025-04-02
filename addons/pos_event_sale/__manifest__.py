# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "PoS - Event Sale",
    'category': "Technical",
    'summary': 'Link module between pos_sale and pos_event',
    'depends': ['pos_event', 'pos_sale'],
    'installable': True,
    'auto_install': True,
    'assets': {
          'web.assets_tests': [
            'pos_event_sale/static/tests/tours/**/*',
        ],
    },
    'license': 'LGPL-3',
}
