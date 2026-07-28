# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Spreadsheet dashboard for purchases",
    'category': 'Hidden',
    'summary': 'Spreadsheet',
    'description': 'Spreadsheet',
    'depends': ['spreadsheet_dashboard', 'purchase'],
    'data': [
        "data/dashboards.xml",
    ],
    'installable': True,
    'auto_install': ['purchase'],
    'license': 'LGPL-3',
}
