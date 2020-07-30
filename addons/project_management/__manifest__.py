# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Project',
    'version': '1.0',
    'website': 'https://www.odoo.com/page/project-management',
    'category': 'Operations/Project',
    'sequence': 10,
    'summary': 'From quotations to invoices',
    'description': """

    """,
    'depends': ['project'],
    'data': [
        'views/project_management_views.xml',
    ],
    'demo': [],
    'application': True,
    'uninstall_hook': 'uninstall_hook',
    'post_init_hook': 'post_init_hook',
}
