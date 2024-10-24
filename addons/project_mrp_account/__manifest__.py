# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Project - Project Manufacturing Analytics",
    'version': '1.0',
    'summary': "Track the costs of manufacturing orders associated with the analytic accounts of your projects.",
    'category': 'Services/Project',
    'depends': ['mrp_account', 'project_mrp'],
    'data': ['views/mrp_production_views.xml'],
    'demo': [
        'data/project_mrp_account_demo.xml',
    ],
    'auto_install': True,
    'license': 'LGPL-3',
}
