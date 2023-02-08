# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Point of Sale Daily Sales Reports',
    'version': '1.0',
    'category': 'Point of Sale',
    'sequence': 6,
    'summary': 'Daily X and Z sales reports of a Point of Sale session',
    'description': """

This module allows the cashier to quickly print a X and a Z sale report
for a given session or a Sales Details for multiple sessions
and configs.

""",
    'depends': ['point_of_sale'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/pos_daily_sales_reports_wizard.xml',
        'views/point_of_sale_view.xml',
    ],
    'installable': True,
    'license': 'LGPL-3',
}
