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
    'demo': [
        'data/pos_restaurant_demo.xml',
    ],
    'installable': True,
    'auto_install': False,
    'assets': {
        'point_of_sale.assets': [
            # inside .
            'pos_restaurant/static/lib/js/jquery.ui.touch-punch.js',
            # inside .
            'pos_restaurant/static/src/js/multiprint.js',
            # inside .
            'pos_restaurant/static/src/js/floors.js',
            # inside .
            'pos_restaurant/static/src/js/notes.js',
            # inside .
            'pos_restaurant/static/src/js/payment.js',
            # inside .
            'pos_restaurant/static/src/js/Resizeable.js',
            # inside .
            'pos_restaurant/static/src/js/Screens/ProductScreen/ControlButtons/OrderlineNoteButton.js',
            # inside .
            'pos_restaurant/static/src/js/Screens/ProductScreen/ControlButtons/TableGuestsButton.js',
            # inside .
            'pos_restaurant/static/src/js/Screens/ProductScreen/ControlButtons/PrintBillButton.js',
            # inside .
            'pos_restaurant/static/src/js/Screens/ProductScreen/ControlButtons/SubmitOrderButton.js',
            # inside .
            'pos_restaurant/static/src/js/Screens/ProductScreen/ControlButtons/SplitBillButton.js',
            # inside .
            'pos_restaurant/static/src/js/Screens/ProductScreen/ControlButtons/TransferOrderButton.js',
            # inside .
            'pos_restaurant/static/src/js/Screens/ProductScreen/Orderline.js',
            # inside .
            'pos_restaurant/static/src/js/Screens/BillScreen.js',
            # inside .
            'pos_restaurant/static/src/js/Screens/SplitBillScreen/SplitBillScreen.js',
            # inside .
            'pos_restaurant/static/src/js/Screens/SplitBillScreen/SplitOrderline.js',
            # inside .
            'pos_restaurant/static/src/js/Screens/FloorScreen/FloorScreen.js',
            # inside .
            'pos_restaurant/static/src/js/Screens/FloorScreen/EditBar.js',
            # inside .
            'pos_restaurant/static/src/js/Screens/FloorScreen/TableWidget.js',
            # inside .
            'pos_restaurant/static/src/js/Screens/FloorScreen/EditableTable.js',
            # inside .
            'pos_restaurant/static/src/js/Screens/OrderManagementScreen/OrderManagementScreen.js',
            # inside .
            'pos_restaurant/static/src/js/Screens/OrderManagementScreen/OrderRow.js',
            # inside .
            'pos_restaurant/static/src/js/Screens/TicketScreen.js',
            # inside .
            'pos_restaurant/static/src/js/ChromeWidgets/BackToFloorButton.js',
            # inside .
            'pos_restaurant/static/src/js/ChromeWidgets/TicketButton.js',
            # inside .
            'pos_restaurant/static/src/js/Chrome.js',
            # inside .
            'pos_restaurant/static/src/js/Screens/ReceiptScreen/ReceiptScreen.js',
            # inside .
            'pos_restaurant/static/src/js/Screens/PaymentScreen.js',
            # inside .
            'pos_restaurant/static/src/js/Screens/TipScreen.js',
            # after //link[@href='/point_of_sale/static/src/css/pos.css']
            ('after', 'point_of_sale/static/src/css/pos.css', 'pos_restaurant/static/src/css/restaurant.css'),
        ],
        'web.assets_backend': [
            # inside .
            'point_of_sale/static/src/scss/pos_dashboard.scss',
        ],
        'web.assets_tests': [
            # inside .
            'pos_restaurant/static/tests/tours/helpers/ProductScreenTourMethods.js',
            # inside .
            'pos_restaurant/static/tests/tours/helpers/ChromeTourMethods.js',
            # inside .
            'pos_restaurant/static/tests/tours/helpers/FloorScreenTourMethods.js',
            # inside .
            'pos_restaurant/static/tests/tours/helpers/SplitBillScreenTourMethods.js',
            # inside .
            'pos_restaurant/static/tests/tours/helpers/TextAreaPopupTourMethods.js',
            # inside .
            'pos_restaurant/static/tests/tours/helpers/TextInputPopupTourMethods.js',
            # inside .
            'pos_restaurant/static/tests/tours/helpers/BillScreenTourMethods.js',
            # inside .
            'pos_restaurant/static/tests/tours/helpers/TipScreenTourMethods.js',
            # inside .
            'pos_restaurant/static/tests/tours/pos_restaurant.js',
            # inside .
            'pos_restaurant/static/tests/tours/SplitBillScreen.tour.js',
            # inside .
            'pos_restaurant/static/tests/tours/ControlButtons.tour.js',
            # inside .
            'pos_restaurant/static/tests/tours/FloorScreen.tour.js',
            # inside .
            'pos_restaurant/static/tests/tours/OrderManagementScreen.tour.js',
            # inside .
            'pos_restaurant/static/tests/tours/TicketScreen.tour.js',
            # inside .
            'pos_restaurant/static/tests/tours/TipScreen.tour.js',
        ],
        'web.assets_qweb': [
            'pos_restaurant/static/src/xml/Resizeable.xml',
            'pos_restaurant/static/src/xml/Chrome.xml',
            'pos_restaurant/static/src/xml/Screens/TicketScreen.xml',
            'pos_restaurant/static/src/xml/Screens/OrderManagementScreen/OrderList.xml',
            'pos_restaurant/static/src/xml/Screens/OrderManagementScreen/OrderRow.xml',
            'pos_restaurant/static/src/xml/Screens/ProductScreen/ControlButtons/OrderlineNoteButton.xml',
            'pos_restaurant/static/src/xml/Screens/ProductScreen/ControlButtons/TableGuestsButton.xml',
            'pos_restaurant/static/src/xml/Screens/ProductScreen/ControlButtons/PrintBillButton.xml',
            'pos_restaurant/static/src/xml/Screens/ProductScreen/ControlButtons/SubmitOrderButton.xml',
            'pos_restaurant/static/src/xml/Screens/ProductScreen/ControlButtons/SplitBillButton.xml',
            'pos_restaurant/static/src/xml/Screens/ProductScreen/ControlButtons/TransferOrderButton.xml',
            'pos_restaurant/static/src/xml/Screens/BillScreen.xml',
            'pos_restaurant/static/src/xml/Screens/SplitBillScreen/SplitBillScreen.xml',
            'pos_restaurant/static/src/xml/Screens/SplitBillScreen/SplitOrderline.xml',
            'pos_restaurant/static/src/xml/Screens/ReceiptScreen/OrderReceipt.xml',
            'pos_restaurant/static/src/xml/Screens/ProductScreen/Orderline.xml',
            'pos_restaurant/static/src/xml/Screens/PaymentScreen/PaymentScreen.xml',
            'pos_restaurant/static/src/xml/Screens/PaymentScreen/PaymentScreenElectronicPayment.xml',
            'pos_restaurant/static/src/xml/Screens/FloorScreen/FloorScreen.xml',
            'pos_restaurant/static/src/xml/Screens/FloorScreen/EditBar.xml',
            'pos_restaurant/static/src/xml/Screens/FloorScreen/TableWidget.xml',
            'pos_restaurant/static/src/xml/Screens/FloorScreen/EditableTable.xml',
            'pos_restaurant/static/src/xml/Screens/TipScreen.xml',
            'pos_restaurant/static/src/xml/ChromeWidgets/BackToFloorButton.xml',
            'pos_restaurant/static/src/xml/multiprint.xml',
            'pos_restaurant/static/src/xml/TipReceipt.xml',
        ],
    }
}
