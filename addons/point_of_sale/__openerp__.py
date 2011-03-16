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
    'name': 'Point Of Sale',
    'version': '1.0',
    'category': 'Generic Modules/Sales & Purchases',
    'description': """
Main features :
===============
    * Fast encoding of the sale.
    * Allow to choose one payment mode (the quick way) or to split the payment between several payment mode.
    * Computation of the amount of money to return.
    * Create and confirm picking list automatically.
    * Allow the user to create invoice automatically.
    * Allow to refund former sales.
    """,
    'author': 'OpenERP SA',
    'images': ['images/cash_registers.jpeg', 'images/pos_analysis.jpeg','images/register_analysis.jpeg','images/sale_order_pos.jpeg'],
    'depends': ['sale', 'delivery'],
    'init_xml': [],

    'update_xml': [
        'security/point_of_sale_security.xml',
        'security/ir.model.access.csv',
        'wizard/pos_details.xml',
        'wizard/pos_add_product.xml',
        'wizard/pos_confirm.xml',
        'wizard/pos_discount.xml',
        'wizard/pos_get_sale.xml',
        'wizard/pos_open_statement.xml',
        'wizard/pos_close_statement.xml',
        'wizard/pos_box_entries.xml',
        'wizard/pos_payment_report_user_view.xml',
        'wizard/pos_payment_report_date_view.xml',
        'wizard/pos_box_out.xml',
        'wizard/pos_sales_user.xml',
        'wizard/all_closed_cashbox_of_the_day.xml',
        'wizard/pos_sales_user_current_user.xml',
        'wizard/pos_sale_user_today.xml',
        'wizard/pos_receipt_view.xml',
        'wizard/pos_payment_report_user.xml',
        'wizard/pos_payment_report.xml',
        'wizard/pos_payment.xml',
        'wizard/pos_scan_product_view.xml',
        'wizard/pos_return_view.xml',
        'point_of_sale_report.xml',
        'point_of_sale_view.xml',
        'report/pos_order_report_view.xml',
        'report/report_cash_register_view.xml',
        'point_of_sale_sequence.xml',
        'point_of_sale_workflow.xml',
        'account_statement_view.xml',
        'account_statement_report.xml',
    ],
    'demo_xml': ['point_of_sale_demo.xml','account_statement_demo.xml'],
    'test': ['test/point_of_sale_test.yml',
            'test/point_of_sale_report.yml',
    ],
    'installable': True,
    'certificate' : '001156338024966477869',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
