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
    'name': 'Purchase Management',
    'version': '1.1',
    'category': 'Generic Modules/Sales & Purchases',
    'description': """
    Purchase module is for generating a purchase order for purchase of goods from a supplier.
    A supplier invoice is created for the particular order placed

    """,
    'author': 'Tiny',
    'website': 'http://www.openerp.com',
    'depends': ['base', 'account', 'stock', 'process', 'mrp_procurement'],
    'init_xml': [],
    'update_xml': [
                   
        'security/purchase_security.xml',
        'security/ir.model.access.csv',
        'purchase_workflow.xml',
        'purchase_sequence.xml',
        'company_view.xml',
        'purchase_data.xml',
        'wizard/purchase_order_group_view.xml',
        'wizard/purchase_installer.xml',
        'wizard/purchase_line_invoice_view.xml',
        'purchase_view.xml',
        'purchase_report.xml',
        'stock_view.xml',
        'partner_view.xml',
        'process/purchase_process.xml',
        'report/purchase_report_view.xml',
    ],
    'demo_xml': ['purchase_demo.xml','purchase_unit_test.xml'],
    'installable': True,
    'active': False,
    'certificate': '0057234283549',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
