# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'IoT features for Work Order',
    'version': '1.0',
    'category': 'Manufacturing/Manufacturing',
    'sequence': 50,
    'summary': 'Steps in MRP work orders with IoT devices',
    'depends': ['mrp_workorder', 'quality_iot'],
    'description': """
Configure IoT devices to be used in certain 
steps for taking measures, taking pictures, ...
""",
    "data": [
        'security/ir.model.access.csv',
        'views/mrp_workorder_views.xml',
    ],
    'auto_install': True,
    'license': 'OEEL-1',
}
