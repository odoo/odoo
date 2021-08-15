# -*- coding: utf-8 -*-
{
    'name': 'Website Live Chat',
    'category': 'Hidden',
    'summary': 'Chat with your website visitors',
    'version': '1.0',
    'description': """
Allow website visitors to chat with the collaborators. This module also brings a feedback tool for the livechat and web pages to display your channel with its ratings on the website.
    """,
    'depends': ['website', 'im_livechat'],
    'installable': True,
    'application': False,
    'auto_install': True,
    'data': [
        'views/assets.xml',
        'views/website_livechat.xml',
        'views/res_config_settings_views.xml',
        'views/website_livechat_view.xml',
        'views/website_visitor_views.xml',
        'security/ir.model.access.csv',
        'security/website_livechat.xml',
        'data/website_livechat_data.xml',
    ],
    'qweb': [
        'static/src/bugfix/bugfix.xml',
        'static/src/bugfix/public_bugfix.xml',
        'static/src/components/discuss/discuss.xml',
        'static/src/components/visitor_banner/visitor_banner.xml',
    ],
    'license': 'LGPL-3',
}
