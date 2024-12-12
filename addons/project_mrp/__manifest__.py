# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Project Manufacturing',
    'version': '1.0',
    'summary': 'Link the manufacturing orders to your projects.',
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
