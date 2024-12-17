# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Spreadsheet dashboard for Point of Sale",
    'version': '1.0',
    'category': 'Hidden',
    'summary': 'POS dashboard',
    'description': 'Dashboard spreadsheet',
    'depends': ['spreadsheet_dashboard','point_of_sale'],
    'data': [
        "data/dashboards.xml",
    ],
    'installable': True,
    'auto_install': ['point_of_sale'],
    'license': 'LGPL-3',
}
