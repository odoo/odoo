# -*- coding: utf-8 -*-
{
    'name': 'Mollie Payments',
    'version': '13.0.1',
    'author': 'Mollie',
    'website': 'http://www.mollie.com',
    'category': 'eCommerce',
    'description': """
        Mollie helps businesses of all sizes to sell and build
         more efficiently with a solid but easy-to-use payment solution.
         Start growing your business today with effortless payments.
    """,
    'depends': ["sale", "base", "payment", "website_sale", "website", "web",
                "sale_stock"],
    'data': [
        'data/payment_acquirer_data.xml',
        'data/ir_cron.xml',
        'data/method_data.xml',
        'security/ir.model.access.csv',
        'views/payment_views.xml',
        'views/sale_order.xml',
        'views/payment_templates.xml',
    ],
    'images': ['static/images/main_screenshot.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
