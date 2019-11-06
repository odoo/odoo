# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Online Event Ticketing",
    'category': 'Website/Website',
    'summary': "Sell event tickets online",
    'description': """
Sell event tickets through eCommerce app.
    """,
    'depends': ['website_event', 'event_sale', 'website_sale'],
    'data': [
        'data/event_data.xml',
        'views/event_templates.xml',
        'views/event_views.xml',
        'security/ir.model.access.csv',
        'security/website_event_sale_security.xml',
    ],
    'auto_install': True
}
