# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Website Event CRM Questions',
    'version': '1.0',
    'category': 'Marketing/Events',
    'website': 'https://www.odoo.com/app/events',
    'description': """
        Add information when we build the description of a lead to include
        the questions and answers linked to the registrations.
    """,
    'depends': ['website_event_crm', 'website_event_questions'],
    'installable': True,
    'auto_install': True,
    'license': 'LGPL-3',
}
