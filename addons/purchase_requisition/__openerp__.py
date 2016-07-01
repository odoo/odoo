# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Purchase Requisitions',
    'version': '0.1',
    'category': 'Purchases',
    'website': 'https://www.odoo.com/page/purchase',
    'description': """
This module allows you to manage your Purchase Requisition.
===========================================================

When a purchase order is created, you now have the opportunity to save the
related requisition. This new object will regroup and will allow you to easily
keep track and order all your purchase orders.
""",
    'depends' : ['purchase'],
    'demo': ['purchase_requisition_demo.xml'],
    'data': [
        'security/purchase_tender.xml',
        'purchase_requisition_data.xml',
        'purchase_requisition_view.xml',
        'purchase_requisition_report.xml',
        'security/ir.model.access.csv',
        'views/report_purchaserequisition.xml',
    ],
    'auto_install': False,
    'test': [
        'test/purchase_requisition_users.yml',
        'test/purchase_requisition_demo.yml',
        'test/cancel_purchase_requisition.yml',
        'test/purchase_requisition.yml',
    ],
    'installable': True,
}
