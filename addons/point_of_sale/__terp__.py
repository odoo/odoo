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
    'name': 'Point Of Sale',
    'version': '1.0',
    'category': 'Generic Modules/Sales & Purchases',
    'description': """
Main features :
 - Fast encoding of the sale.
 - Allow to choose one payment mode (the quick way) or to split the payment between several payment mode.
 - Computation of the amount of money to return.
 - Create and confirm picking list automatically.
 - Allow the user to create invoice automatically.
 - Allow to refund former sales.

    """,
    'author': 'Tiny',
    'depends': ['sale', 'delivery','report_mrp'],
#    'depends': ['sale', 'purchase', 'account', 'account_tax_include','board','mrp','board_manufacturing','delivery','profile_manufacturing','account','multi_company'],
    'init_xml': [
        'security/point_of_sale_security.xml',
        'security/ir.model.access.csv',
        'pos_report.xml',
        'pos_wizard.xml',
        'pos_view.xml',
        'pos_sequence.xml',
        'posrule_data.xml',
        'pos_data.xml',
        'pos_workflow.xml',
        'statement_view.xml',
        'statement_report.xml', 
        'statement_data.xml',
        'statement_wizard.xml'
    ],
    'update_xml': [
        'security/point_of_sale_security.xml',
        'security/ir.model.access.csv',
        'pos_report.xml',
        'pos_wizard.xml',
        'pos_view.xml',
        'pos_sequence.xml',
        'posrule_data.xml',
        'pos_data.xml',
        'pos_workflow.xml'
    ],
    'demo_xml': ['pos_demo.xml','singer_statement_demo.xml','multi_company_stock_data.xml'],
    'installable': True,
    'certificate': '',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
