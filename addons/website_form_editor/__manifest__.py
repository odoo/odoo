# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Form Builder',
    'category': 'Website',
    'summary': 'Build custom web forms',
    'version': '1.0',
    'description': """
Customize and create your own web forms.
This module adds a new building block in the website builder in order to build new forms from scratch in any website page.
    """,
    'depends': ['website_enterprise', 'website_form'],
    'data': [
        'data/mail_mail_data.xml',
        'views/website_form_editor_templates.xml',
        'views/snippets.xml',
        'views/ir_model_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'OEEL-1',
}
