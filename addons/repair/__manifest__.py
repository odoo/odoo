# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Repairs',
    'version': '1.0',
    'sequence': 200,
    'category': 'Manufacturing',
    'summary': 'Repair damaged products',
    'description': """
The aim is to have a complete module to manage all products repairs.
====================================================================

The following topics are covered by this module:
------------------------------------------------------
    * Add/remove products in the reparation
    * Impact for stocks
    * Invoicing (products and/or services)
    * Warranty concept
    * Repair quotation report
    * Notes for the technician and for the final customer
""",
    'depends': ['stock', 'sale_management', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'security/repair_security.xml',
        'wizard/repair_cancel_views.xml',
        'wizard/repair_make_invoice_views.xml',
        'wizard/stock_warn_insufficient_qty_views.xml',
        'views/repair_views.xml',
        'report/repair_reports.xml',
        'report/repair_templates_repair_order.xml',
        'data/ir_sequence_data.xml',
        'data/repair_data.xml',
    ],
    'demo': ['data/repair_demo.xml'],
    'test': [],
    'installable': True,
    'auto_install': False,
    'application': True,
}
