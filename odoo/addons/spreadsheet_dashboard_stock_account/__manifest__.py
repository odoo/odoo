# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Spreadsheet dashboard for stock",
    'category': 'Hidden',
    'summary': 'Spreadsheet',
    'description': 'Spreadsheet',
    'depends': ['spreadsheet_dashboard', 'stock_account'],
    'data': [
        "data/dashboards.xml",
    ],
    'installable': True,
    'auto_install': ['stock_account'],
    'license': 'LGPL-3',
}
