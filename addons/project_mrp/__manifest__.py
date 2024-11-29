# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "MRP Project",
    'version': '1.0',
    'summary': "Monitor MRP using project",
    'category': 'Services/Project',
    'depends': ['mrp', 'project'],
    'data': [
        'views/mrp_bom_views.xml',
        'views/mrp_production_views.xml',
        'views/project_project_views.xml',
    ],
    'auto_install': True,
    'license': 'LGPL-3',
}
