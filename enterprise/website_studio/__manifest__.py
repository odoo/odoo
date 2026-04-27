# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Website Studio",
    'summary': "Display Website Elements in Studio",
    'description': """
Studio - Customize Odoo
=======================

This addon allows the user to display all the website forms linked to a certain
model. Furthermore, you can create a new website form or edit an existing one.

""",
    'category': 'Hidden',
    'version': '1.0',
    'depends': [
        'web_studio',
        'website',
    ],
    'data': [
        'views/templates.xml',
        'views/views.xml',
        'views/snippets/s_website_form.xml',
    ],
    'auto_install': True,
    'license': 'OEEL-1',
    'assets': {
        'web_studio.studio_assets_minimal': [
            'website_studio/static/src/editor_tabs.js',
        ],
        'web.assets_tests': [
            'website_studio/static/tests/tours/**/*',
        ],
        'website.backend_assets_all_wysiwyg': [
            'website_studio/static/src/website_form_editor.js',
        ]
    }
}
