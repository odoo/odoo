# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Helpdesk: Help Center',
    'category': 'Services/Helpdesk',
    'sequence': 58,
    'summary': 'Help Center for helpdesk based on Odoo Forum',
    'depends': [
        'website_forum',
        'website_helpdesk',
    ],
    'description': """
Website Forum integration for the helpdesk module
=================================================

    Allow your teams to have related forums to answer customer questions.
    Transform tickets into questions on the forum with a single click.

    """,
    'data': [
        'security/ir.model.access.csv',
        'views/forum_forum_templates.xml',
        'views/helpdesk_templates.xml',
        'views/helpdesk_views.xml',
        'views/forum_forum_views.xml',
        'wizards/helpdesk_ticket_select_forum.xml',
    ],
    'demo': [
        'data/helpdesk_demo.xml',
        'data/website_helpdesk_forum_demo.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'website_helpdesk_forum/static/src/**/*',
        ],
        'web.assets_tests': [
            'website_helpdesk_forum/static/tests/tours/**/*',
        ],
    },
    'auto_install': True,
    'license': 'OEEL-1',
}
