# -*- coding: utf-8 -*-

{
    'name': "Online Event's Tickets",
    'category': 'Marketing',
    'summary': "Manage Events & Sell Tickets Online",
    'website': 'https://www.odoo.com/page/events',
    'description': """
Online Event's Tickets
======================

        """,
    'depends': ['website_event', 'event_sale', 'website_sale'],
    'data': [
        'data/data.xml',
        'views/website_event_sale_templates.xml',
        'security/ir.model.access.csv',
        'security/website_event_sale_security.xml',
    ],
    'auto_install': True
}
