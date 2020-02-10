# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Delivery Costs',
    'version': '1.0',
    'category': 'Stock',
    'description': """
Allows you to add delivery methods in sale orders and picking.
==============================================================

You can define your own carrier for prices. When creating
invoices from picking, the system is able to add and compute the shipping line.
""",
    'depends': ['sale_stock', 'sale_management'],
    'data': [
        'security/ir.model.access.csv',
        'security/delivery_carrier_security.xml',
        'views/product_packaging_view.xml',
        'views/delivery_view.xml',
        'views/partner_view.xml',
        'views/product_template_view.xml',
        'data/delivery_data.xml',
        'data/mail_template_data.xml',
        'views/report_shipping.xml',
        'views/report_deliveryslip.xml',
        'views/report_package_barcode.xml',
        'views/res_config_settings_views.xml',
        'wizard/choose_delivery_package_views.xml',
        'views/assets.xml',
    ],
    'demo': ['data/delivery_demo.xml'],
    'installable': True,
}
