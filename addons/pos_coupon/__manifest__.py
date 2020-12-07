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
            'pos_coupon/static/src/css/coupon.css',
            'pos_coupon/static/src/js/**/*.js',
        ],
        'web.assets_tests': [
            'pos_coupon/static/tests/tours/**/*',
        ],
        'web.assets_qweb': [
            'pos_coupon/static/src/xml/**/*',
        ],
    }
}
