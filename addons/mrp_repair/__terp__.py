# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################


{
    'name': 'Products Repairs Module',
    'version': '1.0',
    'category': 'Custom',
    'description': """
           The aim is to have a complete module to manage all products repairs. The following topics should be covered by this module:
           * Add/remove products in the reparation
           * Impact for stocks
           * Invoicing (products and/or services)
           * Warranty concept
           * Repair quotation report
           * Notes for the technician and for the final customer           
""",
    'author': 'Tiny',
    'depends': ['base', 'sale', 'account'],
    'update_xml': [
        'security/ir.model.access.csv',
        'mrp_repair_sequence.xml',
        'mrp_repair_wizard.xml',
        'mrp_repair_view.xml',
        'mrp_repair_workflow.xml',
        'mrp_repair_report.xml'
    ],
    'demo_xml': [],
    'installable': True,
    'active': False,
    'certificate': '0060814381277',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
