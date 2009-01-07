# -*- encoding: utf-8 -*-
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
    'name': 'Stock Management',
    'version': '1.0',
    'category': 'Generic Modules/Inventory Control',
    'description': """Module provides Inventory Management, define warehouse, stock location, Pickings, 
    Incoming products, Outgoing products, Internal movements of product, Traceability.
    Reports for stock like lots by location, Stock Forecast, Item Labels, Picking List etc.. 
     """,
    'author': 'Tiny',
    'website': 'http://www.openerp.com',
    'depends': ['product', 'account'],
    'init_xml': [],
    'update_xml': [
        'stock_workflow.xml',
        'stock_data.xml',
        'stock_incoterms.xml',
        'stock_wizard.xml',
        'stock_view.xml',
        'stock_report.xml',
        'stock_sequence.xml',
        'product_data.xml',
        'product_view.xml',
        'partner_view.xml',
        'report_stock_view.xml',
        'security/stock_security.xml',
        'security/ir.model.access.csv'
    ],
    'demo_xml': ['stock_demo.xml'],
    'installable': True,
    'active': False,
    'certificate': '55421559965',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
