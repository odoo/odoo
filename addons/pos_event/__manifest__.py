# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "POS - Event",
    'category': "Technical",
    'summary': 'Link module between Point of Sale and Event',
    'depends': ['point_of_sale', 'event_product'],
    'data': [
        'data/point_of_sale_data.xml',
        'data/event_product_data.xml',
        'views/event_registration_views.xml',
        'views/event_event_views.xml',
        'views/pos_order_views.xml',
        'security/ir.access.csv',
    ],
    'demo': [
        'data/event_product_demo.xml',
        'data/point_of_sale_demo.xml',
    ],
    'auto_install': True,
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_event/static/src/**/*',
        ],
        'web.assets_tests': [
            'pos_event/static/tests/tours/**/*',
        ],
        'web.assets_unit_tests': [
            'pos_event/static/tests/unit/**/*'
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
