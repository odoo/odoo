# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Mailing List Archive',
    'category': 'Website',
    'description': """
Odoo Mail Group : Mailing List Archives
==========================================

        """,
    'depends': ['website_mail'],
    'data': [
        'data/mail_template_data.xml',
        'views/website_mail_channel_templates.xml',
        'views/snippets.xml',
    ],
}
