# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Website Mail',
    'category': 'Hidden',
    'summary': 'Website Module for Mail',
    'version': '0.1',
    'description': """Glue module holding mail improvements for website.""",
    'depends': ['website', 'mail'],
    'data': [
        'views/website_mail_templates.xml',
        'data/mail_channel_data.xml',
    ],
    'qweb': [
        'static/src/xml/chatter_message.xml'
    ],
    'installable': True,
    'auto_install': True,
}
