# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Online Task Submission',
    'category': 'Website/Website',
    'summary': 'Add a task suggestion form to your website',
    'version': '1.0',
    'description': """
Generate tasks in Project app from a form published on your website. This module requires the use of the *Form Builder* module (available in Odoo Enterprise) in order to build the form.
    """,
    'depends': ['website', 'project'],
    'data': [
        'data/website_form_project_data.xml',
        ],
    'installable': True,
    'auto_install': True,
    'assets': {
        'website.assets_wysiwyg': [
            'website_form_project/static/src/js/website_form_project_editor.js',
        ],
    },
    'license': 'LGPL-3',
}
