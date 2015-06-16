# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Inter Company Module for Sale/Purchase Orders and Invoices',
    'version': '1.1',
    'summary': 'Intercompany SO/PO/INV rules',
    'description': ''' Module for synchronization of Documents between several companies. For example, this allow you to have a Sale Order created automatically when a Purchase Order is validated with another company of the system as supplier, and inversely.

    Supported documents are SO, PO and invoices/refunds.
''',
    'author': 'Odoo SA',
    'website': 'http://www.odoo.com',
    'depends': [
        'sale',
        'purchase',
        'sale_stock',
        'sale_order_dates'
    ],
    'data': [
        'views/inter_company_so_po_view.xml',
        'views/res_config_view.xml',
    ],
    'test': [
    #TODO: need to move these tests in python test suite (Accounting test case)
        # 'test/test_intercompany_data.yml',
        # 'test/inter_company_so_to_po.yml',
        # 'test/inter_company_po_to_so.yml',
        # 'test/inter_company_invoice.yml'
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,
}
