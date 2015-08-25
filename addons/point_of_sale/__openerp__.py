# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Point of Sale',
    'version': '1.0.1',
    'category': 'Point Of Sale',
    'sequence': 20,
    'summary': 'Touchscreen Interface for Shops',
    'description': """
Quick and Easy sale process
===========================

This module allows you to manage your shop sales very easily with a fully web based touchscreen interface.
It is compatible with all PC tablets and the iPad, offering multiple payment methods.

Product selection can be done in several ways:

* Using a barcode reader
* Browsing through categories of products or via a text search.

Main Features
-------------
* Fast encoding of the sale
* Choose one payment method (the quick way) or split the payment between several payment methods
* Computation of the amount of money to return
* Create and confirm the picking list automatically
* Allows the user to create an invoice automatically
* Refund previous sales
    """,
    'depends': ['sale_stock', 'barcodes'],
    'data': [
        'data/report_paperformat.xml',
        'data/default_barcode_patterns.xml',
        'security/point_of_sale_security.xml',
        'security/ir.model.access.csv',
        'wizard/pos_box.xml',
        'wizard/pos_confirm.xml',
        'wizard/pos_details.xml',
        'wizard/pos_discount.xml',
        'wizard/pos_open_statement.xml',
        'wizard/pos_payment.xml',
        'views/templates.xml',
        'point_of_sale.xml',
        'point_of_sale_report.xml',
        'point_of_sale_view.xml',
        'point_of_sale_sequence.xml',
        'point_of_sale_data.xml',
        'report/pos_order_report_view.xml',
        'point_of_sale_workflow.xml',
        'account_statement_view.xml',
        'account_statement_report.xml',
        'res_users_view.xml',
        'res_partner_view.xml',
        'res_config_view.xml',
        'views/report_statement.xml',
        'views/report_usersproduct.xml',
        'views/report_receipt.xml',
        'views/report_saleslines.xml',
        'views/report_detailsofsales.xml',
        'views/report_payment.xml',
        'views/report_sessionsummary.xml',
        'views/report_userlabel.xml',
        'views/point_of_sale.xml',
        'point_of_sale_dashboard.xml',
    ],
    'demo': [
        'point_of_sale_demo.xml',
    ],
    'test': [
        '../account/test/account_minimal_test.xml',
        'test/tests_before.xml',
        'test/00_register_open.yml',
        'test/01_order_to_payment.yml',
        'test/02_order_to_invoice.yml',
        'test/point_of_sale_report.yml',
        'test/account_statement_reports.yml',
    ],
    'installable': True,
    'application': True,
    'qweb': ['static/src/xml/pos.xml'],
    'website': 'https://www.odoo.com/page/point-of-sale',
    'auto_install': False,
}
