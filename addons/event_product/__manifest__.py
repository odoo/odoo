# -*- coding: utf-8 -*-

{
    'name': 'Events Product',
    'version': '1.0',
    'category': 'Marketing/Events',
    'website': 'https://www.odoo.com/app/events',
    'description': """
This module serves as bridge module that'll be used for both Sale and 
Point of Sale. It allows to link ticket and product
""",
    'depends': ['event', 'product'],
    'data': [
        'views/event_registration_views.xml',
        'views/event_ticket_views.xml',
        'data/event_product_data.xml',
        'report/event_product_report_views.xml',
        'security/ir.model.access.csv',
        'security/ir_rule.xml',
    ],
    'demo': [
        'data/event_product_demo.xml',
    ],
    'auto_install': False,
    'license': 'LGPL-3',
}
