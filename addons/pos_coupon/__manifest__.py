# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name": "Point of Sale Coupons",
    "version": "1.0",
    "category": "Sales/Point Of Sale",
    "sequence": 6,
    "summary": "Use coupons in Point of Sale",
    "description": "",
    "depends": ["coupon", "point_of_sale"],
    "data": [
        "data/mail_template_data.xml",
        'data/default_barcode_patterns.xml',
        "security/ir.model.access.csv",
        "views/coupon_views.xml",
        "views/coupon_program_views.xml",
        "views/pos_config_views.xml",
        "views/res_config_settings_views.xml",
        ],
    "demo": [
        "demo/pos_coupon_demo.xml",
    ],
    "installable": True,
    'assets': {
        'point_of_sale.assets': [
            # inside .
            'pos_coupon/static/src/css/coupon.css',
            # inside .
            'pos_coupon/static/src/js/coupon.js',
            # inside .
            'pos_coupon/static/src/js/Orderline.js',
            # inside .
            'pos_coupon/static/src/js/PaymentScreen.js',
            # inside .
            'pos_coupon/static/src/js/ProductScreen.js',
            # inside .
            'pos_coupon/static/src/js/ActivePrograms.js',
            # inside .
            'pos_coupon/static/src/js/ControlButtons/PromoCodeButton.js',
            # inside .
            'pos_coupon/static/src/js/ControlButtons/ResetProgramsButton.js',
        ],
        'web.assets_tests': [
            # inside .
            'pos_coupon/static/src/js/tours/PosCouponTourMethods.js',
            # inside .
            'pos_coupon/static/src/js/tours/PosCoupon1.tour.js',
            # inside .
            'pos_coupon/static/src/js/tours/PosCoupon2.tour.js',
        ],
        'web.assets_qweb': [
            "pos_coupon/static/src/xml/ControlButtons/PromoCodeButton.xml",
            "pos_coupon/static/src/xml/ControlButtons/ResetProgramsButton.xml",
            "pos_coupon/static/src/xml/ActivePrograms.xml",
            "pos_coupon/static/src/xml/OrderReceipt.xml",
            "pos_coupon/static/src/xml/OrderWidget.xml",
        ],
    }
}
