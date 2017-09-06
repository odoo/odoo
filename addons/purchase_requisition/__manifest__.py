# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Purchase Agreements',
    'version': '0.1',
    'category': 'Purchases',
    'website': 'https://www.odoo.com/page/purchase',
    'description': """
This module allows you to manage your Purchase Agreements.
===========================================================

Manage calls for tenders and blanket orders. Calls for tenders are used to get
competing offers from different vendors and select the best ones. Blanket orders
are agreements you have with vendors to benefit from a predetermined pricing.
""",
    'depends' : ['purchase'],
    'demo': ['data/purchase_requisition_demo.xml'],
    'data': [
        'security/purchase_tender.xml',
        'security/ir.model.access.csv',
        'data/purchase_requisition_data.xml',
        'views/purchase_requisition_views.xml',
        'views/res_config_settings_views.xml',
        'report/purchase_requisition_report.xml',
        'report/report_purchaserequisition.xml',
    ],
}
