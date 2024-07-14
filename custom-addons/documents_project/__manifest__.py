# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Documents - Projects',
    'version': '1.0',
    'category': 'Productivity/Documents',
    'summary': 'Project from documents',
    'description': """
Add the ability to create invoices from the document module.
""",
    'website': ' ',
    'depends': ['documents', 'project'],
    'data': [
        'data/documents_folder_data.xml',
        'data/documents_facet_data.xml',
        'data/documents_tag_data.xml',
        'data/documents_workflow_data.xml',
        'views/documents_folder_views.xml',
        'views/documents_facet_views.xml',
        'views/documents_tag_views.xml',
        'views/documents_document_views.xml',
        'views/project_views.xml',
        'views/documents_templates_share.xml',
        'views/project_templates.xml',
    ],
    'demo': [
        'data/documents_project_demo.xml',
    ],
    'auto_install': True,
    'license': 'OEEL-1',
    'post_init_hook': '_documents_project_post_init',
}
