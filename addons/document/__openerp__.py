# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Attachments List and Document Indexation',
    'version': '2.1',
    'category': 'Knowledge Management',
    'description': """
Attachments list and document indexation
========================================
* Show attachment on the top of the forms
* Document Indexation: odt
""",
    'depends': ['web'],
    'data': [
        'views/document.xml',
    ],
    'installable': True,
    'auto_install': False,
}
