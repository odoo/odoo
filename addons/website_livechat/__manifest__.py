# -*- coding: utf-8 -*-
{
    'name': 'Website Live Chat',
    'category': 'Technical Settings',
    'summary': 'Chat with your website visitors',
    'version': '1.0',
    'description': """
Allow website visitors to chat with the collaborators. This module also brings a feedback tool for the livechat and web pages to display your channel with its ratings on the website.
    """,
    'depends': ['website', 'im_livechat'],
    'installable': True,
    'application': True,
    'auto_install': True,
    'data': [
        'views/website_livechat.xml',
        'views/res_config_settings_views.xml',
        'views/website_livechat_view.xml',
        'security/ir.model.access.csv',
        'security/website_livechat.xml',
        'data/website_livechat_data.xml',
    ],
}
