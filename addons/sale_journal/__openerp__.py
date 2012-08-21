# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

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
    'author': 'OpenERP SA',
    'website': 'http://www.openerp.com',
    'images': ['images/invoice_type.jpeg'],
    'depends': ['sale'],
    'init_xml': ['sale_journal_data.xml'],
    'update_xml': [
        'security/ir.model.access.csv',
        'sale_journal_view.xml',
    ],
    'demo_xml': ['sale_journal_demo.xml'],
    'test': [ ],
    'installable': True,
    'auto_install': False,
    'certificate': '0077661619085',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
