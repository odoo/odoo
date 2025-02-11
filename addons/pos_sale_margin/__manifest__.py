# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'POS - Sale Margin',
    'version': '1.1',
    'category': 'Hidden',
    'summary': 'Link module between Point of Sale and Sales Margin',
    'description': """

This module adds enable you to view the margin of your Point of Sale orders in the Sales Margin report.
""",
    'depends': ['pos_sale', 'sale_margin'],
    'installable': True,
    'auto_install': True,
    'license': 'LGPL-3',
}
