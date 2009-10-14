# -*- coding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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
    "name" : "Stock Management",
    "version" : "1.1",
    "author" : "Tiny",
    "description" : """OpenERP Stock Management module can manage multi-warehouses, multi and structured stock locations.
Thanks to the double entry management, the inventory controlling is powerful and flexible:
* Moves history and planning,
* Different inventory methods (FIFO, LIFO, ...)
* Stock valuation (standard or average price, ...)
* Robustness faced with Inventory differences
* Automatic reordering rules (stock level, JIT, ...)
* Bar code supported
* Rapid detection of mistakes through double entry system
* Traceability (upstream/downstream, production lots, serial number, ...)
    """,
    "website" : "http://www.openerp.com",
    "depends" : ["product", "account"],
    "category" : "Generic Modules/Inventory Control",
    "init_xml" : [],
    "demo_xml" : ["stock_demo.xml"],
    "update_xml" : [
        "stock_workflow.xml", 
        "stock_data.xml", 
        "stock_incoterms.xml",
        "stock_wizard.xml", 
        "stock_view.xml", 
        "stock_report.xml", 
        "stock_sequence.xml", 
        "product_data.xml",
        "product_view.xml",
        "partner_view.xml",
        "report_stock_view.xml",
        "security/stock_security.xml",
        "security/ir.model.access.csv",
    ],
    'demo_xml': ['stock_demo.xml'],
    'installable': True,
    'active': False,
    'certificate': '0055421559965',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
