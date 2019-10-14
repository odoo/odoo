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
        'views/assets.xml',
        'views/website_mail_templates.xml',
    ],
    'installable': True,
    'auto_install': True,
}
