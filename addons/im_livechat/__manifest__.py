# -*- coding: utf-8 -*-
{
    'name' : 'Live Chat',
    'version': '1.0',
    'sequence': 170,
    'summary': 'Chat with your website visitors',
    'category': 'Website/Live Chat',
    'complexity': 'easy',
    'website': 'https://www.odoo.com/page/live-chat',
    'description':
        """
Live Chat Support
==========================

Allow to drop instant messaging widgets on any web page that will communicate
with the current server and dispatch visitors request amongst several live
chat operators.
Help your customers with this chat, and analyse their feedback.

        """,
    'data': [
        "data/mail_shortcode_data.xml",
        "data/mail_data.xml",
        "data/im_livechat_channel_data.xml",
        "security/im_livechat_channel_security.xml",
        "security/ir.model.access.csv",
        "views/rating_views.xml",
        "views/mail_channel_views.xml",
        "views/im_livechat_channel_views.xml",
        "views/im_livechat_channel_templates.xml",
        "views/res_users_views.xml",
        "report/im_livechat_report_channel_views.xml",
        "report/im_livechat_report_operator_views.xml"
    ],
    'demo': [
        "data/im_livechat_channel_demo.xml",
        'data/mail_shortcode_demo.xml',
    ],
    'depends': ["mail", "rating"],
    'qweb': ['static/src/xml/*.xml'],
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'LGPL-3',
}
