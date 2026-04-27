# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Worksheet for Quality Control',
    'version': '1.0',
    'category': 'Manufacturing/Quality',
    'summary': 'Create custom worksheet for quality control',
    'depends': ['quality_control', 'worksheet'],
    'description': """
Create customizable worksheet for Quality Control.
""",
    "data": [
        'security/quality_control_security.xml',
        'security/ir.model.access.csv',
        'data/quality_control_data.xml',
        'views/quality_views.xml',
        'views/worksheet_template_views.xml',
        'report/worksheet_custom_report_templates.xml',
    ],
    "demo": [
        'data/quality_worksheet_demo.xml',
    ],
    'license': 'OEEL-1',
    'assets': {
        'web.assets_backend': [
            'quality_control_worksheet/static/**/*',
        ],
    }
}
