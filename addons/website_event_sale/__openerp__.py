# -*- coding: utf-8 -*-

{
    'name': "Online Event's Tickets",
    'category': 'Hidden',
    'summary': "Sell Your Event's Tickets",
    'website': 'https://www.odoo.com/page/events',
    'version': '1.0',
    'description': """
Online Event's Tickets
======================

        """,
    'author': 'OpenERP SA',
    'depends': ['website_event', 'event_sale', 'website_sale'],
    'data': [
        'views/website_event_sale.xml',
        'security/ir.model.access.csv',
        'security/website_event_sale.xml',
    ],
    'qweb': ['static/src/xml/*.xml'],
    'installable': True,
    'auto_install': True
}
