# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "MRP Account Project",
    'version': '1.0',
    'summary': "Monitor MRP account using project",
    'category': 'Services/Project',
    'depends': ['mrp_account', 'project_mrp'],
    'data': ['views/mrp_production_views.xml'],
    'demo': [
        'data/project_mrp_account_demo.xml',
    ],
    'auto_install': True,
    'license': 'LGPL-3',
}
