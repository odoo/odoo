# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Website Slides Helpdesk',
    'category': 'Services/Helpdesk',
    'sequence': 58,
    'summary': 'Ticketing, Support, Slides',
    'depends': [
        'website_helpdesk',
        'website_slides',
    ],
    'description': """
Website Slides integration for the helpdesk module
==================================================

    Add slide presentations to your team so customers seeking help can see them those before submitting new tickets.

    """,
    'data': [
        'views/helpdesk_views.xml',
        'views/helpdesk_templates.xml',
        'views/slide_channel_views.xml',
    ],
    'auto_install': True,
    'license': 'OEEL-1',
}
