# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Point of Sale Cash Rounding',
    'version': '1.0.0',
    'category': 'Sales/Point Of Sale',
    'sequence': 20,
    'summary': 'Allow specific rounding in pos',
    'description': "",
    'depends': ['point_of_sale'],
    'data': [
        'views/res_config_settings_view.xml',
        'views/pos_config_view.xml',
        'views/account_cash_rounding_view.xml',
        'views/pos_order_view.xml',
        'views/pos_template.xml',
    ],
    'qweb': [
        'static/src/xml/pos.xml',
    ],
    'installable': True,
    'auto_install': True,
}
