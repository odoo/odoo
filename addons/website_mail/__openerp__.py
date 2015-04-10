# -*- coding: utf-8 -*-

{
    'name': 'Website Mail',
    'category': 'Hidden',
    'summary': 'Website Module for Mail',
    'version': '0.1',
    'description': """Glue module holding mail improvements for website.""",
    'author': 'Odoo S.A.',
    'depends': ['website', 'mail'],
    'data': [
        'views/website_mail_snippets.xml',
        'views/website_mail_templates.xml',
        'views/website_mail_designer_views.xml',
        'views/website_mail_snippet_options.xml',
        'views/website_mail_theme_list.xml',
        'views/theme/neopolitan_snippets.xml',
        'views/theme/skyline_snippets.xml',
        'views/theme/narrative_snippets.xml',
        'views/theme/sunday_snippets.xml',
        'views/theme/go_snippets.xml',
        'views/theme/airmail_snippets.xml',
        'views/theme/zenflat_snippets.xml',
        'views/theme/cleave_snippets.xml',
        'data/mail_group_data.xml',
    ],
    'qweb': [
        'static/src/xml/website_mail.xml'
    ],
    'installable': True,
    'auto_install': True,
}
