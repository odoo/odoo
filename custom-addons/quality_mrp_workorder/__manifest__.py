# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'MRP features for Quality Control',
    'version': '1.0',
    'category': 'Manufacturing/Quality',
    'sequence': 50,
    'summary': 'Quality Management with MRP',
    'depends': ['quality_control', 'mrp_workorder', 'barcodes'],
    'description': """
Adds Quality Control to workorders.
""",
    "data": [
        'views/quality_views.xml',
        'views/mrp_workorder_views.xml',
        'report/worksheet_custom_report_templates.xml',
    ],
    "demo": [
        'data/mrp_workorder_demo.xml'
    ],
    'assets': {
        'web.assets_backend': [
            'quality_mrp_workorder/static/src/**/*.xml',
            'quality_mrp_workorder/static/src/**/*.js',
        ],
    },
    'auto_install': True,
    'license': 'OEEL-1',
}
