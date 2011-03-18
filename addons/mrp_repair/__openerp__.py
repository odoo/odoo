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
    'name': 'Products Repairs Module - Manage All products Repairs',
    'version': '1.0',
    'category': 'Tools',
    'description': """
           The aim is to have a complete module to manage all products repairs. The following topics should be covered by this module:
           ===========================================================================================================================

           * Add/remove products in the reparation
           * Impact for stocks
           * Invoicing (products and/or services)
           * Warranty concept
           * Repair quotation report
           * Notes for the technician and for the final customer
""",
    'author': 'OpenERP SA',
    'images': ['images/repair_order.jpeg'],
    'depends': ['mrp', 'sale', 'account'],
    'update_xml': [
        'security/ir.model.access.csv',
        'mrp_repair_sequence.xml',
        'wizard/mrp_repair_cancel_view.xml',
        'wizard/mrp_repair_make_invoice_view.xml',
        'mrp_repair_view.xml',
        'mrp_repair_workflow.xml',
        'mrp_repair_report.xml',
    ],
    'demo_xml': [],
    'test': ['test/test_mrp_repair.yml', 'test/mrp_repair_report.yml'],
    'installable': True,
    'active': False,
    'certificate': '0060814381277',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
