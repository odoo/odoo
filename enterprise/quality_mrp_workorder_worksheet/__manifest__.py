# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Quality Worksheet for Workorder',
    'version': '1.0',
    'category': 'Manufacturing/Quality',
    'summary': 'Quality Worksheet for Workorder',
    'depends': ['quality_control_worksheet', 'quality_mrp_workorder'],
    'description': """
Create customizable quality worksheet for workorder.
""",
    "data": [
        'views/quality_views.xml',
    ],
    "demo": [
        'data/mrp_workorder_demo.xml',
    ],
    'assets': {
        'web.assets_tests': [
            'quality_mrp_workorder_worksheet/static/tests/tours/**/*',
        ],
    },
    'auto_install': True,
    'license': 'OEEL-1',
}
