# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Purchase Requisitions',
    'version': '0.1',
    'category': 'Purchase Management',
    'website': 'https://www.odoo.com/page/purchase',
    'description': """
This module allows you to manage your Purchase Requisition.
===========================================================

When a purchase order is created, you now have the opportunity to save the
related requisition. This new object will regroup and will allow you to easily
keep track and order all your purchase orders.
""",
    'depends' : ['purchase'],
    'demo': ['data/purchase_requisition_demo.xml'],
    'data': [
             'security/purchase_tender.xml',
             'security/ir.model.access.csv',
             'views/purchase_requisition.xml',
             'wizard/purchase_requisition_partner_view.xml',
             'wizard/bid_line_qty_view.xml',
             'data/purchase_requisition_data.xml',
             'views/purchase_requisition_view.xml',
             'views/purchase_requisition_report.xml',
             'views/purchase_requisition_workflow.xml',
             'data/purchase_requisition_sequence.xml',
             'views/report_purchaserequisition.xml',
    ],
    'qweb': [
        'static/src/xml/purchase_requisition.xml',
    ],
}
