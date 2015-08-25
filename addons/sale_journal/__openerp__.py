# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Invoicing Journals',
    'version': '1.0',
    'category': 'Sales Management',
    'description': """
The sales journal modules allows you to categorise your sales and deliveries (picking lists) between different journals.
========================================================================================================================

This module is very helpful for bigger companies that works by departments.

You can use journal for different purposes, some examples:
----------------------------------------------------------
    * isolate sales of different departments
    * journals for deliveries by truck or by UPS

Journals have a responsible and evolves between different status:
-----------------------------------------------------------------
    * draft, open, cancel, done.

Batch operations can be processed on the different journals to confirm all sales
at once, to validate or invoice packing.

It also supports batch invoicing methods that can be configured by partners and sales orders, examples:
-------------------------------------------------------------------------------------------------------
    * daily invoicing
    * monthly invoicing

Some statistics by journals are provided.
    """,
    'website': 'https://www.odoo.com/page/billing',
    'depends': ['sale_stock'],
    'data': [
        'security/ir.model.access.csv',
        'sale_journal_view.xml',
        'sale_journal_data.xml'
    ],
    'demo': ['sale_journal_demo.xml'],
    'test': [ ],
    'installable': True,
    'auto_install': False,
}
