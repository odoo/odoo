# -*- coding: utf-8 -*-

{
    'name': 'Discuss',
    'version': '1.0',
    'category': 'Discuss',
    'sequence': 25,
    'summary': 'Discussions, Mailing Lists, News',
    'description': """
Business oriented Social Networking
===================================
The Social Networking module provides a unified social network abstraction layer allowing applications to display a complete
communication history on documents with a fully-integrated email and message management system.

It enables the users to read and send messages as well as emails. It also provides a feeds page combined to a subscription mechanism that allows to follow documents and to be constantly updated about recent news.

Main Features
-------------
* Clean and renewed communication history for any Odoo document that can act as a discussion topic
* Subscription mechanism to be updated about new messages on interesting documents
* Unified feeds page to see recent messages and activity on followed documents
* User communication through the feeds page
* Threaded discussion design on documents
* Relies on the global outgoing mail server - an integrated email management system - allowing to send emails with a configurable scheduler-based processing engine
* Includes an extensible generic email composition assistant, that can turn into a mass-mailing assistant and is capable of interpreting simple *placeholder expressions* that will be replaced with dynamic data when each email is actually sent.
    """,
    'website': 'https://www.odoo.com/page/enterprise-social-network',
    'depends': ['base', 'base_setup', 'bus'],
    'data': [
        'wizard/invite_view.xml',
        'wizard/mail_compose_message_view.xml',
        'views/mail_message_subtype_views.xml',
        'views/mail_tracking_views.xml',
        'views/mail_message_views.xml',
        'views/mail_mail_views.xml',
        'views/mail_followers_views.xml',
        'views/mail_channel_views.xml',
        'views/mail_shortcode_views.xml',
        'views/res_config_views.xml',
        'data/mail_data.xml',
        'data/mail_channel_data.xml',
        'data/mail_shortcode_data.xml',
        'security/mail_security.xml',
        'security/ir.model.access.csv',
        'views/mail_alias_views.xml',
        'views/res_users_views.xml',
        'views/mail_templates.xml',
        'wizard/email_template_preview_view.xml',
        'views/mail_template_views.xml',
        'views/ir_actions_views.xml',
        'views/res_partner_views.xml',
        'views/contact_views.xml',
    ],
    'demo': [
        'data/mail_demo.xml',
        'data/mail_channel_demo.xml',
    ],
    'installable': True,
    'application': True,
    'qweb': [
        'static/src/xml/client_action.xml',
        'static/src/xml/composer.xml',
        'static/src/xml/chatter.xml',
        'static/src/xml/systray.xml',
        'static/src/xml/thread.xml',
        'static/src/xml/chat_window.xml',
        'static/src/xml/announcement.xml',
    ],
}
