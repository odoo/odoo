# -*- coding: utf-8 -*-
{
    'name': "aumet_pos_theme",
    'summary': """
       """,
    'description': """
    """,
    'website': "",
    'category': 'Point of Sale',
    'version': '14.0.0.3',
    # any module necessary for this one to work correctly
    'depends': ['point_of_sale', 'flexipharmacy', 'pos_hr', 'pos_discount'],

    # always loaded
    'data': [
        'views/assets.xml',
    ],

    'qweb': [
        'static/src/xml/*.xml',
        'static/src/xml/Screens/Chrome.xml',
        'static/src/xml/Screens/DiscountButton.xml',
        'static/src/xml/Screens/ProductScreen/ProductItem.xml',
        'static/src/xml/Screens/ProductScreen/OrderWidget.xml',
        'static/src/xml/Screens/ProductScreen/Orderline.xml',
        'static/src/xml/Screens/ProductScreen/CashBoxOpening.xml',
        'static/src/xml/Screens/ProductScreen/ProductScreen.xml',
        'static/src/xml/Screens/ProductScreen/ActionpadWidget.xml',
        'static/src/xml/Screens/ProductScreen/ProductsWidgetControlPanel.xml',
        'static/src/xml/Screens/ProductScreen/CustomControlButtons/MiddleCustomControlButton.xml',
        'static/src/xml/ChromeWidgets/TicketButton.xml',
        'static/src/xml/ChromeWidgets/OpenDetailButton.xml',
        'static/src/xml/ChromeWidgets/PharmacyDetailSidebar.xml',

        'static/src/xml/Screens/PaymentScreen/PaymentScreen.xml',
        'static/src/xml/Screens/PaymentScreen/PaymentScreenStatus.xml',

    ],
    "auto_install": False,
    "installable": True,
}
