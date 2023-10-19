# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Online Task Submission',
    'category': 'Website/Website',
    'summary': 'Add a task suggestion form to your website',
    'version': '1.0',
    'description': """
Generate tasks in Project app from a form published on your website. This module requires the use of the *Form Builder* module in order to build the form.
    """,
    'depends': ['website', 'project'],
    'data': [
        'data/website_project_data.xml',
        'views/project_portal_project_task_template.xml',
        'views/project_portal_project_project_template.xml',
        ],
    'installable': True,
    'auto_install': True,
    'assets': {
        'website.assets_wysiwyg': [
            'website_project/static/src/js/website_project_editor.js',
        ],
        'project.webclient': [
            # In website, there is a patch of the LinkDialog (see
            # website/static/src/js/editor/editor.js) that require the utils.js.
            # Thus, when website is installed, this bundle need to have the
            # utils.js in its assets, otherwise, there will be an unmet
            # dependency.
            'website/static/src/js/utils.js',
            'web/static/src/core/autocomplete/*',
            'website/static/src/components/autocomplete_with_pages/*',
        ],
    },
    'license': 'LGPL-3',
}
