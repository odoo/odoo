# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Project Manufacturing',
    'summary': 'Link manufacturing orders to your projects.',
    'category': 'Services/Project',
    'depends': ['mrp', 'project'],
    'data': [
        'views/mrp_bom_views.xml',
        'views/mrp_production_views.xml',
        'views/project_project_views.xml',
        'security/ir.access.csv',
    ],
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
