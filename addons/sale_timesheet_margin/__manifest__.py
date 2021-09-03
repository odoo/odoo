# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Service Margins in Sales Orders',
    'version': '1.0',
    'summary': 'Bridge module between Sales Margin and Sales Timesheet',
    'description': """
Allows to compute accurate margin for Service sales.
======================================================
""",
    'category': 'Hidden',
    'depends': ['sale_margin', 'sale_timesheet'],
    'demo': [],
    'data': [],
    'auto_install': True,
    'license': 'LGPL-3',
}
