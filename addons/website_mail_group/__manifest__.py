# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Website Mail Group",
    'summary': "Add a website snippet for the mail groups.",
    'description': "",
    'version': '1.0',
    'depends': ['mail_group', 'website'],
    'auto_install': True,
    'data': [
        'views/snippets/s_group.xml',
        'views/snippets/snippets.xml',
        'views/mail_group_views.xml',
        'views/website_mail_group_menus.xml',
    ],
    'assets': {
        'website.assets_wysiwyg': [
            'website_mail_group/static/src/snippets/s_group/options.js',
        ],
        'web.assets_frontend': [
            'website_mail_group/static/src/snippets/s_group/000.js',
        ],
    },
    'license': 'LGPL-3',
}
