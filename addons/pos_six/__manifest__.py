# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'POS Six',
    'version': '1.0',
    'category': 'Sales/Point Of Sale',
    'sequence': 6,
    'summary': 'Integrate your POS with a Six payment terminal',
    'description': '',
    'data': [
        'views/pos_payment_method_views.xml',
        'views/point_of_sale_assets.xml',
    ],
    'qweb': [
        'static/src/xml/BalanceButton.xml',
        'static/src/xml/Chrome.xml',
    ],
    'depends': ['point_of_sale'],
    'installable': True,
    'license': 'LGPL-3',
}
