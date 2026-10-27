# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Purchase Agreements',
    'version': '0.1',
    'category': 'Inventory/Purchase',
    'description': """
This module allows you to manage your Purchase Agreements.
===========================================================

Manage calls for tenders and blanket orders. Calls for tenders are used to get
competing offers from different vendors and select the best ones. Blanket orders
are agreements you have with vendors to benefit from a predetermined pricing.
""",
    'depends': ['purchase'],
    'demo': ['data/purchase_requisition_demo.xml'],
    'data': [
        'security/purchase_requisition_security.xml',
        'security/ir.model.access.csv',
        'data/purchase_requisition_data.xml',
        'views/product_views.xml',
        'views/purchase_views.xml',
        'views/purchase_requisition_views.xml',
        'report/purchase_requisition_report.xml',
        'report/report_purchaserequisition.xml',
        'wizard/purchase_requisition_alternative_warning.xml',
        'wizard/purchase_requisition_create_alternative.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'purchase_requisition/static/src/*/**.js',
            'purchase_requisition/static/src/views/*/**.js',
            'purchase_requisition/static/src/*/**.scss',
            'purchase_requisition/static/src/*/**.xml',
        ],
    },
    'license': 'LGPL-3',
}
