# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Website Mail',
    'category': 'Hidden',
    'summary': 'Website Module for Mail',
    'version': '0.1',
    'description': """
Module holding mail improvements for website. It holds the follow widget.
""",
    'depends': ['website', 'mail'],
    'data': [
        'views/website_mail_templates.xml',
    ],
    'installable': True,
    'auto_install': True,
    'assets': {
        'web.assets_frontend': [
            'website_mail/static/src/interactions/follow.js',
            'website_mail/static/src/css/website_mail.scss',
        ],
        'web.assets_edit_frontend': [
            'website/static/src/interactions/follow.edit.js',
        ],
    },
    'license': 'LGPL-3',
}
