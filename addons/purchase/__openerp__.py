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
    'category': 'Purchase Management',
    'sequence': 19,
    'summary': 'Purchase Orders, Receptions, Supplier Invoices',
    'description': """
Manage goods requirement by Purchase Orders easily
==================================================

Purchase management enables you to track your suppliers' price quotations and convert them into purchase orders if necessary.
OpenERP has several methods of monitoring invoices and tracking the receipt of ordered goods. You can handle partial deliveries in OpenERP, so you can keep track of items that are still to be delivered in your orders, and you can issue reminders automatically.

OpenERP’s replenishment management rules enable the system to generate draft purchase orders automatically, or you can configure it to run a lean process driven entirely by current production needs.

Dashboard / Reports for Purchase Management will include:
---------------------------------------------------------
* Request for Quotations
* Purchase Orders Waiting Approval 
* Monthly Purchases by Category
* Receptions Analysis
* Purchase Analysis
    """,
    'author': 'OpenERP SA',
    'website': 'http://www.openerp.com',
    'images' : ['images/purchase_order.jpeg', 'images/purchase_analysis.jpeg', 'images/request_for_quotation.jpeg'],
    'depends': ['stock', 'process', 'procurement'],
    'data': [
        'security/purchase_security.xml',
        'security/ir.model.access.csv',
        'purchase_workflow.xml',
        'purchase_sequence.xml',
        'company_view.xml',
        'purchase_data.xml',
        'wizard/purchase_order_group_view.xml',
        'wizard/purchase_line_invoice_view.xml',
        'purchase_report.xml',
        'purchase_view.xml',
        'stock_view.xml',
        'partner_view.xml',
        'process/purchase_process.xml',
        'report/purchase_report_view.xml',
        'board_purchase_view.xml',
        'edi/purchase_order_action_data.xml',
        'res_config_view.xml',
    ],
    'test': [
        'test/process/cancel_order.yml',
        'test/process/rfq2order2done.yml',
        'test/process/generate_invoice_from_reception.yml',
        'test/process/run_scheduler.yml',
        'test/process/merge_order.yml',
        'test/process/edi_purchase_order.yml',
        'test/process/invoice_on_poline.yml',
        'test/ui/print_report.yml',
        'test/ui/duplicate_order.yml',
        'test/ui/delete_order.yml',
    ],
    'demo': [
        'purchase_order_demo.yml',
        'purchase_demo.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
