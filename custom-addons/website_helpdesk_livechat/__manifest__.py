# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Website IM Livechat Helpdesk',
    'category': 'Services/Helpdesk',
    'sequence': 58,
    'summary': 'Ticketing, Support, Livechat',
    'depends': [
        'website_helpdesk',
        'website_livechat',
    ],
    'description': """
Website IM Livechat integration for the helpdesk module
=======================================================

Features:

    - Have a team-related livechat channel to answer your customer's questions.
    - Create new tickets with ease using commands in the channel.

    """,
    'data': [
        'data/helpdesk_livechat_chatbot_data.xml',

        'views/chatbot_script_views.xml',
        'views/chatbot_script_step_views.xml',
        'views/helpdesk_view.xml',
    ],
    'auto_install': True,
    'license': 'OEEL-1',
    'post_init_hook': '_create_livechat_channel',
    'assets': {
        'web.assets_backend': [
            'website_helpdesk_livechat/static/src/**/*',
        ],
        'mail.assets_public': [
            'website_helpdesk_livechat/static/src/**/*',
        ],
        'web.tests_assets': [
            'website_helpdesk_livechat/static/tests/helpers/**/*',
        ],
        'web.qunit_suite_tests': [
            'website_helpdesk_livechat/static/tests/**/*',
            ('remove', 'website_helpdesk_livechat/static/tests/helpers/**/*'),
        ],
    },
}
