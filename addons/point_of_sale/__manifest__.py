# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Point of Sale',
    'version': '1.0.1',
    'category': 'Sales/Point of Sale',
    'sequence': 40,
    'summary': 'User-friendly PoS interface for shops and restaurants',
    'description': "",
    'depends': ['stock_account', 'barcodes', 'web_editor', 'digest'],
    'data': [
        'security/point_of_sale_security.xml',
        'security/ir.model.access.csv',
        'data/default_barcode_patterns.xml',
        'data/digest_data.xml',
        'wizard/pos_box.xml',
        'wizard/pos_details.xml',
        'wizard/pos_payment.xml',
        'wizard/pos_close_session_wizard.xml',
        'views/pos_assets_common.xml',
        'views/pos_assets_index.xml',
        'views/pos_assets_qunit.xml',
        'views/point_of_sale_report.xml',
        'views/point_of_sale_view.xml',
        'views/pos_order_view.xml',
        'views/pos_category_view.xml',
        'views/product_view.xml',
        'views/account_journal_view.xml',
        'views/pos_payment_method_views.xml',
        'views/pos_payment_views.xml',
        'views/pos_config_view.xml',
        'views/pos_session_view.xml',
        'views/point_of_sale_sequence.xml',
        'data/point_of_sale_data.xml',
        'views/pos_order_report_view.xml',
        'views/account_statement_view.xml',
        'views/res_config_settings_views.xml',
        'views/digest_views.xml',
        'views/res_partner_view.xml',
        'views/report_userlabel.xml',
        'views/report_saledetails.xml',
        'views/point_of_sale_dashboard.xml',
    ],
    'demo': [
        'data/point_of_sale_demo.xml',
    ],
    'installable': True,
    'application': True,
    'website': 'https://www.odoo.com/page/point-of-sale-shop',
    'assets': {
        'web.assets_tests': [
            # inside .
            'point_of_sale/static/tests/tours/helpers/utils.js',
            # inside .
            'point_of_sale/static/tests/tours/helpers/ProductScreenTourMethods.js',
            # inside .
            'point_of_sale/static/tests/tours/helpers/TicketScreenTourMethods.js',
            # inside .
            'point_of_sale/static/tests/tours/helpers/PaymentScreenTourMethods.js',
            # inside .
            'point_of_sale/static/tests/tours/helpers/ProductConfiguratorTourMethods.js',
            # inside .
            'point_of_sale/static/tests/tours/helpers/OrderManagementScreenTourMethods.js',
            # inside .
            'point_of_sale/static/tests/tours/helpers/ClientListScreenTourMethods.js',
            # inside .
            'point_of_sale/static/tests/tours/helpers/ReceiptScreenTourMethods.js',
            # inside .
            'point_of_sale/static/tests/tours/helpers/ChromeTourMethods.js',
            # inside .
            'point_of_sale/static/tests/tours/helpers/NumberPopupTourMethods.js',
            # inside .
            'point_of_sale/static/tests/tours/helpers/ErrorPopupTourMethods.js',
            # inside .
            'point_of_sale/static/tests/tours/helpers/SelectionPopupTourMethods.js',
            # inside .
            'point_of_sale/static/tests/tours/helpers/CompositeTourMethods.js',
            # inside .
            'point_of_sale/static/tests/tours/point_of_sale.js',
            # inside .
            'point_of_sale/static/tests/tours/ProductScreen.tour.js',
            # inside .
            'point_of_sale/static/tests/tours/PaymentScreen.tour.js',
            # inside .
            'point_of_sale/static/tests/tours/ProductConfigurator.tour.js',
            # inside .
            'point_of_sale/static/tests/tours/OrderManagementScreen.tour.js',
            # inside .
            'point_of_sale/static/tests/tours/ReceiptScreen.tour.js',
            # inside .
            'point_of_sale/static/tests/tours/Chrome.tour.js',
            # inside .
            'point_of_sale/static/tests/tours/TicketScreen.tour.js',
        ],
        'point_of_sale.assets': [
            # new asset template 
            'web/static/src/scss/fonts.scss',
            # new asset template 
            'web/static/lib/fontawesome/css/font-awesome.css',
            # new asset template 
            'point_of_sale/static/src/css/pos.css',
            # new asset template 
            'point_of_sale/static/src/css/keyboard.css',
            # new asset template 
            'point_of_sale/static/src/css/pos_receipts.css',
            # new asset template 
            'web/static/src/scss/fontawesome_overridden.scss',
            # new asset template 
            'point_of_sale/static/lib/html2canvas.js',
            # new asset template 
            'point_of_sale/static/lib/backbone/backbone.js',
            # new asset template 
            'point_of_sale/static/lib/waitfont.js',
            # new asset template 
            'point_of_sale/static/lib/sha1.js',
            # new asset template 
            'point_of_sale/static/src/js/utils.js',
            # new asset template 
            'point_of_sale/static/src/js/ClassRegistry.js',
            # new asset template 
            'point_of_sale/static/src/js/PosComponent.js',
            # new asset template 
            'point_of_sale/static/src/js/PosContext.js',
            # new asset template 
            'point_of_sale/static/src/js/ComponentRegistry.js',
            # new asset template 
            'point_of_sale/static/src/js/Registries.js',
            # new asset template 
            'point_of_sale/static/src/js/db.js',
            # new asset template 
            'point_of_sale/static/src/js/models.js',
            # new asset template 
            'point_of_sale/static/src/js/keyboard.js',
            # new asset template 
            'point_of_sale/static/src/js/barcode_reader.js',
            # new asset template 
            'point_of_sale/static/src/js/printers.js',
            # new asset template 
            'point_of_sale/static/src/js/Gui.js',
            # new asset template 
            'point_of_sale/static/src/js/PopupControllerMixin.js',
            # new asset template 
            'point_of_sale/static/src/js/ControlButtonsMixin.js',
            # new asset template 
            'point_of_sale/static/src/js/Chrome.js',
            # new asset template 
            'point_of_sale/static/src/js/devices.js',
            # new asset template 
            'point_of_sale/static/src/js/payment.js',
            # new asset template 
            'point_of_sale/static/src/js/custom_hooks.js',
            # new asset template 
            'point_of_sale/static/src/js/Screens/ProductScreen/ProductScreen.js',
            # new asset template 
            'point_of_sale/static/src/js/Screens/ClientListScreen/ClientLine.js',
            # new asset template 
            'point_of_sale/static/src/js/Screens/ClientListScreen/ClientDetailsEdit.js',
            # new asset template 
            'point_of_sale/static/src/js/Screens/ClientListScreen/ClientListScreen.js',
            # new asset template 
            'point_of_sale/static/src/js/Screens/OrderManagementScreen/ControlButtons/InvoiceButton.js',
            # new asset template 
            'point_of_sale/static/src/js/Screens/OrderManagementScreen/ControlButtons/ReprintReceiptButton.js',
            # new asset template 
            'point_of_sale/static/src/js/Screens/OrderManagementScreen/OrderFetcher.js',
            # new asset template 
            'point_of_sale/static/src/js/Screens/OrderManagementScreen/OrderManagementScreen.js',
            # new asset template 
            'point_of_sale/static/src/js/Screens/OrderManagementScreen/MobileOrderManagementScreen.js',
            # new asset template 
            'point_of_sale/static/src/js/Screens/OrderManagementScreen/OrderManagementControlPanel.js',
            # new asset template 
            'point_of_sale/static/src/js/Screens/OrderManagementScreen/OrderList.js',
            # new asset template 
            'point_of_sale/static/src/js/Screens/OrderManagementScreen/OrderRow.js',
            # new asset template 
            'point_of_sale/static/src/js/Screens/OrderManagementScreen/OrderDetails.js',
            # new asset template 
            'point_of_sale/static/src/js/Screens/OrderManagementScreen/OrderlineDetails.js',
            # new asset template 
            'point_of_sale/static/src/js/Screens/OrderManagementScreen/ReprintReceiptScreen.js',
            # new asset template 
            'point_of_sale/static/src/js/Screens/TicketScreen/TicketScreen.js',
            # new asset template 
            'point_of_sale/static/src/js/Screens/PaymentScreen/PSNumpadInputButton.js',
            # new asset template 
            'point_of_sale/static/src/js/Screens/PaymentScreen/PaymentScreenNumpad.js',
            # new asset template 
            'point_of_sale/static/src/js/Screens/PaymentScreen/PaymentScreenElectronicPayment.js',
            # new asset template 
            'point_of_sale/static/src/js/Screens/PaymentScreen/PaymentScreenPaymentLines.js',
            # new asset template 
            'point_of_sale/static/src/js/Screens/PaymentScreen/PaymentScreenStatus.js',
            # new asset template 
            'point_of_sale/static/src/js/Screens/PaymentScreen/PaymentMethodButton.js',
            # new asset template 
            'point_of_sale/static/src/js/Screens/PaymentScreen/PaymentScreen.js',
            # new asset template 
            'point_of_sale/static/src/js/Screens/ProductScreen/Orderline.js',
            # new asset template 
            'point_of_sale/static/src/js/Screens/ProductScreen/OrderSummary.js',
            # new asset template 
            'point_of_sale/static/src/js/Screens/ProductScreen/OrderWidget.js',
            # new asset template 
            'point_of_sale/static/src/js/Screens/ProductScreen/NumpadWidget.js',
            # new asset template 
            'point_of_sale/static/src/js/Screens/ProductScreen/ActionpadWidget.js',
            # new asset template 
            'point_of_sale/static/src/js/Screens/ProductScreen/CategoryBreadcrumb.js',
            # new asset template 
            'point_of_sale/static/src/js/Screens/ProductScreen/CategoryButton.js',
            # new asset template 
            'point_of_sale/static/src/js/Screens/ProductScreen/CategorySimpleButton.js',
            # new asset template 
            'point_of_sale/static/src/js/Screens/ProductScreen/HomeCategoryBreadcrumb.js',
            # new asset template 
            'point_of_sale/static/src/js/Screens/ProductScreen/ProductsWidgetControlPanel.js',
            # new asset template 
            'point_of_sale/static/src/js/Screens/ProductScreen/ProductItem.js',
            # new asset template 
            'point_of_sale/static/src/js/Screens/ProductScreen/ProductList.js',
            # new asset template 
            'point_of_sale/static/src/js/Screens/ProductScreen/ProductsWidget.js',
            # new asset template 
            'point_of_sale/static/src/js/Screens/ReceiptScreen/WrappedProductNameLines.js',
            # new asset template 
            'point_of_sale/static/src/js/Screens/ReceiptScreen/OrderReceipt.js',
            # new asset template 
            'point_of_sale/static/src/js/Screens/ReceiptScreen/ReceiptScreen.js',
            # new asset template 
            'point_of_sale/static/src/js/Screens/ScaleScreen/ScaleScreen.js',
            # new asset template 
            'point_of_sale/static/src/js/ChromeWidgets/CashierName.js',
            # new asset template 
            'point_of_sale/static/src/js/ChromeWidgets/ProxyStatus.js',
            # new asset template 
            'point_of_sale/static/src/js/ChromeWidgets/SyncNotification.js',
            # new asset template 
            'point_of_sale/static/src/js/ChromeWidgets/OrderManagementButton.js',
            # new asset template 
            'point_of_sale/static/src/js/ChromeWidgets/HeaderButton.js',
            # new asset template 
            'point_of_sale/static/src/js/ChromeWidgets/SaleDetailsButton.js',
            # new asset template 
            'point_of_sale/static/src/js/ChromeWidgets/TicketButton.js',
            # new asset template 
            'point_of_sale/static/src/js/Misc/Draggable.js',
            # new asset template 
            'point_of_sale/static/src/js/Misc/NotificationSound.js',
            # new asset template 
            'point_of_sale/static/src/js/Misc/IndependentToOrderScreen.js',
            # new asset template 
            'point_of_sale/static/src/js/Misc/AbstractReceiptScreen.js',
            # new asset template 
            'point_of_sale/static/src/js/Misc/SearchBar.js',
            # new asset template 
            'point_of_sale/static/src/js/ChromeWidgets/DebugWidget.js',
            # new asset template 
            'point_of_sale/static/src/js/Popups/AbstractAwaitablePopup.js',
            # new asset template 
            'point_of_sale/static/src/js/Popups/ErrorPopup.js',
            # new asset template 
            'point_of_sale/static/src/js/Popups/ErrorBarcodePopup.js',
            # new asset template 
            'point_of_sale/static/src/js/Popups/ConfirmPopup.js',
            # new asset template 
            'point_of_sale/static/src/js/Popups/TextInputPopup.js',
            # new asset template 
            'point_of_sale/static/src/js/Popups/TextAreaPopup.js',
            # new asset template 
            'point_of_sale/static/src/js/Popups/ErrorTracebackPopup.js',
            # new asset template 
            'point_of_sale/static/src/js/Popups/SelectionPopup.js',
            # new asset template 
            'point_of_sale/static/src/js/Popups/EditListInput.js',
            # new asset template 
            'point_of_sale/static/src/js/Popups/EditListPopup.js',
            # new asset template 
            'point_of_sale/static/src/js/Popups/NumberPopup.js',
            # new asset template 
            'point_of_sale/static/src/js/Popups/OfflineErrorPopup.js',
            # new asset template 
            'point_of_sale/static/src/js/Popups/OrderImportPopup.js',
            # new asset template 
            'point_of_sale/static/src/js/Popups/ProductConfiguratorPopup.js',
            # new asset template 
            'point_of_sale/static/src/js/Popups/CashOpeningPopup.js',
            # new asset template 
            'point_of_sale/static/src/js/Screens/ProductScreen/ControlButtons/SetPricelistButton.js',
            # new asset template 
            'point_of_sale/static/src/js/Screens/ProductScreen/ControlButtons/SetFiscalPositionButton.js',
            # new asset template 
            'point_of_sale/static/src/js/ChromeWidgets/ClientScreenButton.js',
            # new asset template 
            'point_of_sale/static/src/js/Misc/NumberBuffer.js',
            # new asset template 
            'point_of_sale/static/src/js/Misc/MobileOrderWidget.js',
            # new asset template 
            'point_of_sale/static/src/js/Notification.js',
        ],
        'web.assets_backend': [
            # inside .
            'point_of_sale/static/src/scss/pos_dashboard.scss',
            # inside .
            'point_of_sale/static/src/js/tours/point_of_sale.js',
            # inside .
            'point_of_sale/static/src/js/debug_manager.js',
            # inside .
            'point_of_sale/static/src/js/web_overrides/pos_config_form.js',
        ],
        'point_of_sale.pos_assets_backend': [
            # Is primary with parent
            ('include', 'web.assets_backend'),
            # None None
            # There is no content in this asset...
        ],
        'web.assets_qweb': [
            'point_of_sale/static/src/xml/Chrome.xml',
            'point_of_sale/static/src/xml/debug_manager.xml',
            'point_of_sale/static/src/xml/Screens/ProductScreen/ProductScreen.xml',
            'point_of_sale/static/src/xml/Screens/ClientListScreen/ClientLine.xml',
            'point_of_sale/static/src/xml/Screens/ClientListScreen/ClientDetailsEdit.xml',
            'point_of_sale/static/src/xml/Screens/ClientListScreen/ClientListScreen.xml',
            'point_of_sale/static/src/xml/Screens/OrderManagementScreen/ControlButtons/InvoiceButton.xml',
            'point_of_sale/static/src/xml/Screens/OrderManagementScreen/ControlButtons/ReprintReceiptButton.xml',
            'point_of_sale/static/src/xml/Screens/OrderManagementScreen/OrderManagementScreen.xml',
            'point_of_sale/static/src/xml/Screens/OrderManagementScreen/MobileOrderManagementScreen.xml',
            'point_of_sale/static/src/xml/Screens/OrderManagementScreen/OrderManagementControlPanel.xml',
            'point_of_sale/static/src/xml/Screens/OrderManagementScreen/OrderList.xml',
            'point_of_sale/static/src/xml/Screens/OrderManagementScreen/OrderRow.xml',
            'point_of_sale/static/src/xml/Screens/OrderManagementScreen/OrderDetails.xml',
            'point_of_sale/static/src/xml/Screens/OrderManagementScreen/OrderlineDetails.xml',
            'point_of_sale/static/src/xml/Screens/OrderManagementScreen/ReprintReceiptScreen.xml',
            'point_of_sale/static/src/xml/Screens/TicketScreen/TicketScreen.xml',
            'point_of_sale/static/src/xml/Screens/PaymentScreen/PSNumpadInputButton.xml',
            'point_of_sale/static/src/xml/Screens/PaymentScreen/PaymentScreenNumpad.xml',
            'point_of_sale/static/src/xml/Screens/PaymentScreen/PaymentScreenElectronicPayment.xml',
            'point_of_sale/static/src/xml/Screens/PaymentScreen/PaymentScreenPaymentLines.xml',
            'point_of_sale/static/src/xml/Screens/PaymentScreen/PaymentScreenStatus.xml',
            'point_of_sale/static/src/xml/Screens/PaymentScreen/PaymentMethodButton.xml',
            'point_of_sale/static/src/xml/Screens/PaymentScreen/PaymentScreen.xml',
            'point_of_sale/static/src/xml/Screens/ProductScreen/Orderline.xml',
            'point_of_sale/static/src/xml/Screens/ProductScreen/OrderSummary.xml',
            'point_of_sale/static/src/xml/Screens/ProductScreen/OrderWidget.xml',
            'point_of_sale/static/src/xml/Screens/ProductScreen/NumpadWidget.xml',
            'point_of_sale/static/src/xml/Screens/ProductScreen/ActionpadWidget.xml',
            'point_of_sale/static/src/xml/Screens/ProductScreen/CategoryBreadcrumb.xml',
            'point_of_sale/static/src/xml/Screens/ProductScreen/CategoryButton.xml',
            'point_of_sale/static/src/xml/Screens/ProductScreen/CategorySimpleButton.xml',
            'point_of_sale/static/src/xml/Screens/ProductScreen/HomeCategoryBreadcrumb.xml',
            'point_of_sale/static/src/xml/Screens/ProductScreen/ProductsWidgetControlPanel.xml',
            'point_of_sale/static/src/xml/Screens/ProductScreen/ProductItem.xml',
            'point_of_sale/static/src/xml/Screens/ProductScreen/ProductList.xml',
            'point_of_sale/static/src/xml/Screens/ProductScreen/ProductsWidget.xml',
            'point_of_sale/static/src/xml/Screens/ReceiptScreen/WrappedProductNameLines.xml',
            'point_of_sale/static/src/xml/Screens/ReceiptScreen/OrderReceipt.xml',
            'point_of_sale/static/src/xml/Screens/ReceiptScreen/ReceiptScreen.xml',
            'point_of_sale/static/src/xml/Screens/ScaleScreen/ScaleScreen.xml',
            'point_of_sale/static/src/xml/ChromeWidgets/CashierName.xml',
            'point_of_sale/static/src/xml/ChromeWidgets/ProxyStatus.xml',
            'point_of_sale/static/src/xml/ChromeWidgets/SyncNotification.xml',
            'point_of_sale/static/src/xml/ChromeWidgets/OrderManagementButton.xml',
            'point_of_sale/static/src/xml/ChromeWidgets/HeaderButton.xml',
            'point_of_sale/static/src/xml/ChromeWidgets/SaleDetailsButton.xml',
            'point_of_sale/static/src/xml/ChromeWidgets/TicketButton.xml',
            'point_of_sale/static/src/xml/CustomerFacingDisplay/CustomerFacingDisplayOrder.xml',
            'point_of_sale/static/src/xml/SaleDetailsReport.xml',
            'point_of_sale/static/src/xml/Misc/Draggable.xml',
            'point_of_sale/static/src/xml/Misc/NotificationSound.xml',
            'point_of_sale/static/src/xml/Misc/SearchBar.xml',
            'point_of_sale/static/src/xml/ChromeWidgets/DebugWidget.xml',
            'point_of_sale/static/src/xml/Popups/ErrorPopup.xml',
            'point_of_sale/static/src/xml/Popups/ErrorBarcodePopup.xml',
            'point_of_sale/static/src/xml/Popups/ConfirmPopup.xml',
            'point_of_sale/static/src/xml/Popups/TextInputPopup.xml',
            'point_of_sale/static/src/xml/Popups/TextAreaPopup.xml',
            'point_of_sale/static/src/xml/Popups/ErrorTracebackPopup.xml',
            'point_of_sale/static/src/xml/Popups/SelectionPopup.xml',
            'point_of_sale/static/src/xml/Popups/EditListInput.xml',
            'point_of_sale/static/src/xml/Popups/EditListPopup.xml',
            'point_of_sale/static/src/xml/Popups/NumberPopup.xml',
            'point_of_sale/static/src/xml/Popups/OfflineErrorPopup.xml',
            'point_of_sale/static/src/xml/Popups/OrderImportPopup.xml',
            'point_of_sale/static/src/xml/Popups/ProductConfiguratorPopup.xml',
            'point_of_sale/static/src/xml/Popups/CashOpeningPopup.xml',
            'point_of_sale/static/src/xml/Screens/ProductScreen/ControlButtons/SetPricelistButton.xml',
            'point_of_sale/static/src/xml/Screens/ProductScreen/ControlButtons/SetFiscalPositionButton.xml',
            'point_of_sale/static/src/xml/ChromeWidgets/ClientScreenButton.xml',
            'point_of_sale/static/src/xml/Misc/MobileOrderWidget.xml',
            'point_of_sale/static/src/xml/Notification.xml',
        ],
    }
}
