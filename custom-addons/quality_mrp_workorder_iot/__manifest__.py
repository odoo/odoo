# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'MRP features for Quality Control with IoT',
    'summary': 'Quality Management with MRP and IoT',
    'depends': ['quality_mrp_workorder', 'quality_control_iot', 'mrp_workorder_iot'],
    'category': 'Manufacturing/Quality',
    'description': """
    Adds Quality Control to workorders with IoT.
""",
    "data": [
        'views/mrp_workorder_views.xml',
    ],
    'auto_install': True,
    'license': 'OEEL-1',
}
