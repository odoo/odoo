# -*- coding: utf-8 -*-
{
    'name': 'Sales Coupon',
    'version': '1.0',
    'category': 'Website',
    'author': 'Odoo SA',
    'description': """
Website Sales coupon
===============================

- This model provides the presale coupon facility which can be applied on the purchase of a specific product(on usage base and period base)

- User can create various coupon type which may be bound to date and number of time that coupon can be used.

- In the sales order user gets the information about the coupons allocation as well as expiration.
        """,
    'depends': ['website_sale'],
    'data': [
        'views/website_sale_coupon_view.xml',
        'views/product.xml',
        'views/sale_order.xml',
        'views/report_sale_coupon.xml',
        'views/templates.xml',
        'security/ir.model.access.csv',
        'data/data.xml',
    ],
    'demo': [
        'data/demo.xml',
    ],
    'installable': True,
}
