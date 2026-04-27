# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Maintenance - MRP',
    'version': '1.0',
    'category': 'Manufacturing/Manufacturing',
    'summary': 'Schedule and manage maintenance on machine and tools.',
    'website': 'https://www.odoo.com/app/maintenance',
    'description': """
Maintenance in MRP
==================
* Preventive vs corrective maintenance
* Define different stages for your maintenance requests
* Plan maintenance requests (also recurring preventive)
* Equipment related to workcenters
* MTBF, MTTR, ...
""",
    'depends': ['mrp_workorder', 'maintenance'],
    'data': [
        'data/mrp_maintenance_data.xml',
        'views/maintenance_views.xml',
        'views/mrp_views.xml',
    ],
    'demo': ['data/mrp_maintenance_demo.xml'],
    'assets': {
        'web.assets_backend': [
            'mrp_maintenance/static/src/**/*.js',
            'mrp_maintenance/static/src/**/*.xml',
        ],
    },
    'auto_install': True,
    'license': 'OEEL-1',
}
