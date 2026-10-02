# -*- coding: utf-8 -*-
# Part of Quocent Pvt. Ltd. See LICENSE file for full copyright and licensing details.

{
    # Module Information
    'name': "Action Button in DO to Navigate to Linked SO",
    'category': "Inventory",
    'license': 'LGPL-3',
    'version': '1.0',
    'summary': "Add a button in Delivery Order to navigate to the linked Sales Order.",
    'description': """
        - This module adds a button in the Delivery Order form view to redirect to the linked Sales Order.
        - The button is only visible if the Delivery Order was generated from a Sales Order.
        - If the Delivery Order is not linked to a Sales Order, the button remains hidden.
    """,

    # Dependencies
    'depends': ['base', 'stock', 'sale_management'],

    # Author Information
    'author': "Quocent Digital",
    'website': "https://www.quocent.com",

    # Data Files
    'data': [
        'views/qcent_sale_order_button_view.xml'
    ],

    # Banner
    'images': [
        'static/description/assets/banner.png',
    ],

    # Technical Options
    'installable': True,
    'application': False,
    'auto_install': False,
}
