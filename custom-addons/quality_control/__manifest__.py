# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Quality',
    'version': '1.0',
    'category': 'Manufacturing/Quality',
    'sequence': 120,
    'summary': 'Control the quality of your products',
    'website': 'https://www.odoo.com/app/quality',
    'depends': ['quality'],
    'description': """
Quality Control
===============
* Define quality points that will generate quality checks on pickings,
  manufacturing orders or work orders (quality_mrp)
* Quality alerts can be created independently or related to quality checks
* Possibility to add a measure to the quality check with a min/max tolerance
* Define your stages for the quality alerts
""",
    'data': [
        'data/quality_control_data.xml',
        'report/worksheet_custom_reports.xml',
        'report/worksheet_custom_report_templates.xml',
        'views/quality_views.xml',
        'views/product_views.xml',
        'views/stock_move_views.xml',
        'views/stock_picking_views.xml',
        'views/stock_lot_views.xml',
        'wizard/quality_check_wizard_views.xml',
        'security/ir.model.access.csv',
    ],
    'demo': [
        'data/quality_control_demo.xml',
    ],
    'application': True,
    'license': 'OEEL-1',
    'assets': {
        'web.assets_backend': [
            'quality_control/static/src/**/*',
        ],
    }
}
