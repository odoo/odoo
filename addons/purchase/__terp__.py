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
    'name': 'Purchase Management',
    'version': '1.1',
    'category': 'Generic Modules/Sales & Purchases',
    'description': """Module for purchase management
    Request for quotation, Create Supplier Invoice, Print Order...""",
    'author': 'Tiny',
    'website': 'http://www.openerp.com',
    'depends': ['base', 'account', 'stock', 'process'],
    'init_xml': [],
    'update_xml': [
        'security/purchase_security.xml',
        'security/ir.model.access.csv',
        'purchase_workflow.xml',
        'purchase_sequence.xml',
        'purchase_data.xml',
        'purchase_view.xml',
        'purchase_report.xml',
        'purchase_wizard.xml',
        'stock_view.xml',
        'partner_view.xml',
        'process/purchase_process.xml'
    ],
    'demo_xml': [
        'purchase_demo.xml',
        'test/purchase_test.xml'],
    'installable': True,
    'active': False,
    'certificate': '0057234283549',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
