# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Website Mail Group",
    'summary': "Add a website snippet for the mail groups.",
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
        'web.assets_frontend': [
            'website_mail_group/static/src/snippets/**/*.js',
            ('remove', 'website_mail_group/static/src/**/*.edit.js'),
        ],
        'website.assets_inside_builder_iframe': [
            'website_mail_group/static/src/**/*.edit.js',
        ],
        'website.website_builder_assets': [
            'website_mail_group/static/src/website_builder/**/*',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
