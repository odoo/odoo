# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Repairs Management',
    'version': '1.0',
    'sequence': 200,
    'category': 'Manufacturing',
    'summary': 'Repair broken or damaged products',
    'description': """,
The aim is to have a complete module to manage all products repairs.
====================================================================

The following topics should be covered by this module:
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
        'mrp_repair_sequence.xml',
        'wizard/mrp_repair_cancel_view.xml',
        'wizard/mrp_repair_make_invoice_view.xml',
        'mrp_repair_view.xml',
        'mrp_repair_workflow.xml',
        'mrp_repair_report.xml',

        'views/report_mrprepairorder.xml',
    ],
    'demo': ['mrp_repair_demo.yml'],
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
