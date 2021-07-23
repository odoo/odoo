# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "pos_hr",
    'category': "Hidden",
    'summary': 'Link module between Point of Sale and HR',

    'description': """
        This module adds the possibility to log in to the PoS with Employees using barcode, pin, or both.
        The PoS still requires one user, but it can have an unlimited number of employees.
    """,

    'depends': ['point_of_sale', 'hr'],

    'data': [
        'views/pos_config.xml',
        'views/point_of_sale.xml',
        'views/pos_order_view.xml',
        'views/pos_order_report_view.xml',
    ],
    'installable': True,
    'auto_install': True,
    'qweb': ['static/src/xml/pos.xml'],
    'license': 'LGPL-3',
}
