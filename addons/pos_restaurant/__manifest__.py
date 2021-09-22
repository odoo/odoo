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
    'website': 'https://www.odoo.com/app/point-of-sale-restaurant',
    'data': [
        'security/ir.model.access.csv',
        'views/pos_order_views.xml',
        'views/pos_restaurant_views.xml',
        'views/pos_config_views.xml',
    ],
    'demo': [
        'data/pos_restaurant_demo.xml',
    ],
    'installable': True,
    'auto_install': False,
    'assets': {
        'point_of_sale.assets': [
            'pos_restaurant/static/lib/js/jquery.ui.touch-punch.js',
            'pos_restaurant/static/src/js/multiprint.js',
            'pos_restaurant/static/src/js/floors.js',
            'pos_restaurant/static/src/js/notes.js',
            'pos_restaurant/static/src/js/payment.js',
            'pos_restaurant/static/src/js/Resizeable.js',
            'pos_restaurant/static/src/js/Screens/ProductScreen/ControlButtons/OrderlineNoteButton.js',
            'pos_restaurant/static/src/js/Screens/ProductScreen/ControlButtons/TableGuestsButton.js',
            'pos_restaurant/static/src/js/Screens/ProductScreen/ControlButtons/PrintBillButton.js',
            'pos_restaurant/static/src/js/Screens/ProductScreen/ControlButtons/SubmitOrderButton.js',
            'pos_restaurant/static/src/js/Screens/ProductScreen/ControlButtons/SplitBillButton.js',
            'pos_restaurant/static/src/js/Screens/ProductScreen/ControlButtons/TransferOrderButton.js',
            'pos_restaurant/static/src/js/Screens/ProductScreen/Orderline.js',
            'pos_restaurant/static/src/js/Screens/BillScreen.js',
            'pos_restaurant/static/src/js/Screens/SplitBillScreen/SplitBillScreen.js',
            'pos_restaurant/static/src/js/Screens/SplitBillScreen/SplitOrderline.js',
            'pos_restaurant/static/src/js/Screens/FloorScreen/FloorScreen.js',
            'pos_restaurant/static/src/js/Screens/FloorScreen/EditBar.js',
            'pos_restaurant/static/src/js/Screens/FloorScreen/TableWidget.js',
            'pos_restaurant/static/src/js/Screens/FloorScreen/EditableTable.js',
            'pos_restaurant/static/src/js/Screens/TicketScreen.js',
            'pos_restaurant/static/src/js/ChromeWidgets/BackToFloorButton.js',
            'pos_restaurant/static/src/js/ChromeWidgets/TicketButton.js',
            'pos_restaurant/static/src/js/Chrome.js',
            'pos_restaurant/static/src/js/Screens/ReceiptScreen/ReceiptScreen.js',
            'pos_restaurant/static/src/js/Screens/PaymentScreen.js',
            'pos_restaurant/static/src/js/Screens/TipScreen.js',
            ('after', 'point_of_sale/static/src/css/pos.css', 'pos_restaurant/static/src/css/restaurant.css'),
        ],
        'web.assets_backend': [
            'point_of_sale/static/src/scss/pos_dashboard.scss',
        ],
        'web.assets_tests': [
            'pos_restaurant/static/tests/tours/**/*',
        ],
        'point_of_sale.qunit_suite_tests': [
            'pos_restaurant/static/tests/unit/**/*',
        ],
        'web.assets_qweb': [
            'pos_restaurant/static/src/xml/**/*',
        ],
    },
    'license': 'LGPL-3',
}
