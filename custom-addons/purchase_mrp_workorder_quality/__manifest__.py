
# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Full Traceability Report Demo Data',
    'version': '1.0',
    'category': 'Manufacturing/Manufacturing',
    'sequence': 50,
    'summary': 'Full Traceability Report Demo Data',
    'depends': ['purchase_mrp', 'quality_mrp_workorder', 'purchase_stock'],
    'description': """
Full Traceability Report Demo Data
==================================
""",
    'demo': ['data/purchase_mrp_workorder_quality_demo.xml'],
    'auto_install': True,
    'license': 'OEEL-1',
}
