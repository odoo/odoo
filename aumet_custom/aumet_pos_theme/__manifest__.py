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
    'depends': ['point_of_sale', 'flexipharmacy', 'pos_hr'],

    # always loaded
    'data': [
        'views/templates.xml',
    ],

    'qweb': [
        'static/src/xml/*.xml',
        'static/src/xml/Screens/Chrome.xml',
        'static/src/xml/Screens/ProductScreen/ProductItem.xml',
        'static/src/xml/Screens/ProductScreen/OrderWidget.xml',
        'static/src/xml/Screens/ProductScreen/ProductScreen.xml',
        'static/src/xml/Screens/ProductScreen/ActionpadWidget.xml',
        'static/src/xml/Screens/ProductScreen/ProductsWidgetControlPanel.xml',
        'static/src/xml/ChromeWidgets/HeaderLockButton.xml',
        'static/src/xml/Screens/PaymentScreen/PaymentScreen.xml',
        'static/src/xml/Screens/PaymentScreen/PaymentScreenStatus.xml',
    ],
    "auto_install": False,
    "installable": True,
}
