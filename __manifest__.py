# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Website Form Builder',
    'category': 'Website',
    'summary': 'Build custom web forms using the website builder',
    'version': '1.0',
    'description': """
Odoo Form Editor
====================

Allows you to build web forms on the website using the website builder.
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
