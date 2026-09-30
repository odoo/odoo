# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Spreadsheet dashboard for point of sale",
    'version': '1.0',
    'category': 'Productivity/Dashboard',
    'summary': 'Spreadsheet',
    'description': 'Spreadsheet',
    'depends': ['spreadsheet_dashboard', 'pos_hr'],
    'data': [
        "data/dashboards.xml",
    ],
    'installable': True,
    'auto_install': ['pos_hr'],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
