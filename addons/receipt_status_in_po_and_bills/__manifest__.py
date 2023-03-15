# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name' : 'Show Receipt Status in Purchase order and Vendor bill',
    'version': '16.0.0.1.0',
    'summary': 'Show Receipt Status in Purchase order and Vendor bill',
    'author': "Said YAHIA",
    'website': "https://www.linkedin.com/in/said-yahia-a3a64261",
    'support': "syahia1111@gmail.com",
    'category': 'Sales',
    'depends': ['account','purchase','stock'],
    'installable': True,
    'application': True,
    'auto_install': True,
    'data':[
        # 'views/purchase_order_view.xml',

        'views/account_move_view.xml',

    ],
    'images': ['static/description/banner.png'],
    'demo': [
    ],
    'installable': True,
    'auto_install': True,
    'price': 0,
    'currency': 'USD',
    'license': "AGPL-3",

}
