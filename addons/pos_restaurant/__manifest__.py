# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Restaurant',
    'version': '1.0',
    'category': 'Sales/Point of Sale',
    'sequence': 6,
    'summary': 'Restaurant extensions for the Point of Sale ',
    'description': """

This module adds several features to the Point of Sale that are specific to restaurant management:
- Bill Printing: Allows you to print a receipt before the order is paid
- Bill Splitting: Allows you to split an order into different orders
- Kitchen Order Printing: allows you to print orders updates to kitchen or bar printers

""",
    'depends': ['point_of_sale'],
    'website': 'https://www.odoo.com/page/point-of-sale-restaurant',
    'data': [
        'security/ir.model.access.csv',
        'views/pos_order_views.xml',
        'views/pos_restaurant_views.xml',
        'views/pos_config_views.xml',
        'views/pos_restaurant_templates.xml',
    ],
    'qweb': [
        'static/src/xml/Resizeable.xml',
        'static/src/xml/Chrome.xml',
        'static/src/xml/Screens/TicketScreen.xml',
        'static/src/xml/Screens/OrderManagementScreen/OrderList.xml',
        'static/src/xml/Screens/OrderManagementScreen/OrderRow.xml',
        'static/src/xml/Screens/ProductScreen/ControlButtons/OrderlineNoteButton.xml',
        'static/src/xml/Screens/ProductScreen/ControlButtons/TableGuestsButton.xml',
        'static/src/xml/Screens/ProductScreen/ControlButtons/PrintBillButton.xml',
        'static/src/xml/Screens/ProductScreen/ControlButtons/SubmitOrderButton.xml',
        'static/src/xml/Screens/ProductScreen/ControlButtons/SplitBillButton.xml',
        'static/src/xml/Screens/ProductScreen/ControlButtons/TransferOrderButton.xml',
        'static/src/xml/Screens/BillScreen.xml',
        'static/src/xml/Screens/SplitBillScreen/SplitBillScreen.xml',
        'static/src/xml/Screens/SplitBillScreen/SplitOrderline.xml',
        'static/src/xml/Screens/ReceiptScreen/OrderReceipt.xml',
        'static/src/xml/Screens/ProductScreen/Orderline.xml',
        'static/src/xml/Screens/PaymentScreen/PaymentScreen.xml',
        'static/src/xml/Screens/PaymentScreen/PaymentScreenElectronicPayment.xml',
        'static/src/xml/Screens/FloorScreen/FloorScreen.xml',
        'static/src/xml/Screens/FloorScreen/EditBar.xml',
        'static/src/xml/Screens/FloorScreen/TableWidget.xml',
        'static/src/xml/Screens/FloorScreen/EditableTable.xml',
        'static/src/xml/Screens/TipScreen.xml',
        'static/src/xml/ChromeWidgets/BackToFloorButton.xml',
        'static/src/xml/multiprint.xml',
        'static/src/xml/TipReceipt.xml',
    ],
    'demo': [
        'data/pos_restaurant_demo.xml',
    ],
    'installable': True,
    'auto_install': False,
}
