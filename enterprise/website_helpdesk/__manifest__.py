# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Website Helpdesk',
    'category': 'Hidden',
    'sequence': 57,
    'summary': 'Bridge module for helpdesk modules using the website.',
    'description': 'Bridge module for helpdesk modules using the website.',
    'depends': [
        'helpdesk',
        'website',
    ],
    'data': [
        'data/helpdesk_data.xml',
        'views/helpdesk_views.xml',
        'views/helpdesk_templates.xml',
        'security/website_helpdesk_security.xml',
        'views/snippets.xml',
    ],
    'auto_install': True,
    'license': 'OEEL-1',
    'post_init_hook': '_configure_teams',
    'assets': {
        'web.assets_frontend': [
            'website_helpdesk/static/**/*',
            ('remove', 'website_helpdesk/static/src/js/website_helpdesk_form_editor.js'),
            ('remove', 'website_helpdesk/static/src/js/website_helpdesk_edit_menu.js'),
        ],
        'website.assets_wysiwyg': [
            'website_helpdesk/static/src/js/website_helpdesk_form_editor.js',
        ],
        'website.assets_editor': [
            'website_helpdesk/static/src/js/website_helpdesk_edit_menu.js',
        ]
    }
}
