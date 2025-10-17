# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "MRP Project",
    'summary': "Monitor MRP using project",
    'category': 'Services/Project',
    'depends': ['mrp', 'project'],
    'data': [
        'views/mrp_bom_views.xml',
        'views/mrp_production_views.xml',
        'views/project_project_views.xml',
    ],
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
