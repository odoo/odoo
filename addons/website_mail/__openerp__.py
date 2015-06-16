# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Website Mail',
    'category': 'Hidden',
    'summary': 'Website Module for Mail',
    'version': '0.1',
    'description': """Glue module holding mail improvements for website.""",
    'author': 'OpenERP SA',
    'depends': ['website', 'mail'],
    'data': [
        'views/snippets.xml',
        'views/website_mail.xml',
        'views/website_email_designer.xml',
        'views/snippet_options.xml',
        'views/theme_list.xml',
        'views/theme/neopolitan_snippets.xml',
        'views/theme/skyline_snippets.xml',
        'views/theme/narrative_snippets.xml',
        'views/theme/sunday_snippets.xml',
        'views/theme/go_snippets.xml',
        'views/theme/airmail_snippets.xml',
        'views/theme/zenflat_snippets.xml',
        'views/theme/cleave_snippets.xml',
        'data/mail_groups.xml',
    ],
    'qweb': [
        'static/src/xml/website_mail.xml'
    ],
    'installable': True,
    'auto_install': True,
}
