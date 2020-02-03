# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Website Events CRM',
    'version': '1.0',
    'category': 'Website/Website',
    'website': 'https://www.odoo.com/page/events',
    'description': "Display different types of lead creation for the rule creation",
    'depends': ['event_crm', 'website_event'],
    'data': [
        'views/event_lead_views.xml',
    ],
    'installable': True,
    'auto_install': True,
}
