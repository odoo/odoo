# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Spreadsheet dashboard for stock",
    'category': 'Hidden',
    'summary': 'Spreadsheet',
    'description': 'Spreadsheet',
    'depends': ['spreadsheet_dashboard', 'stock'],
    'data': [
        "data/dashboards.xml",
    ],
    'demo': [],
    'installable': True,
    'auto_install': ['stock'],
    'license': 'LGPL-3',
    'assets': {}
}
