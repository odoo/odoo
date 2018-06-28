# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Task Form',
    'category': 'Website',
    'summary': 'Generate tasks from a contact form',
    'version': '1.0',
    'description': """
Create your own web form which will perform an action of creating a task on the submission button.
    """,
    'depends': ['website_form', 'project'],
    'data': [
        'data/website_form_project_data.xml',
    ],
    'installable': True,
    'auto_install': True,
}
