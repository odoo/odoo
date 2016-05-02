# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Repairs Management',
    'version': '1.0',
    'sequence': 200,
    'category': 'Manufacturing',
    'summary': 'Repair broken or damaged products',
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
    'depends': ['stock', 'sale', 'account'],
    'website': 'https://www.odoo.com/page/manufacturing',
    'data': [
        'security/ir.model.access.csv',
        'security/mrp_repair_security.xml',
        'data/ir_sequence_data.xml',
        'wizard/mrp_repair_cancel_views.xml',
        'wizard/mrp_repair_make_invoice_views.xml',
        'views/mrp_repair_views.xml',
        'data/mrp_repair_data_workflow.xml',
        'report/mrp_repair_reports.xml',
        'report/mrp_repair_templates_repair_order.xml',
    ],
    'demo': ['data/mrp_repair_demo.yml'],
    'test': ['../account/test/account_minimal_test.xml',
             'test/mrp_repair_users.yml',
             'test/test_mrp_repair_noneinv.yml',
             'test/test_mrp_repair_b4inv.yml',
             'test/test_mrp_repair_afterinv.yml',
             'test/test_mrp_repair_cancel.yml',
             'test/test_mrp_repair_fee.yml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}
