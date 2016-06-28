# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Sales Timesheet',
    'version': '1.0',
    'category': 'Hidden',
    'summary': 'Sell based on timesheets',
    'description': """
Allows to sell timesheets in your sales order
=============================================

This module set the right product on all timesheet lines
according to the order/contract you work on. This allows to
have real delivered quantities in sales orders.
""",
    'website': 'https://www.odoo.com/page/warehouse',
    'depends': ['sale', 'hr_timesheet'],
    'data': ['views/sale_timesheet_view.xml',
             'data/sale_timesheet_data.xml',
             'views/sale_service_view.xml',
    ],
    'demo': ['data/sale_timesheet_demo.xml',
        'demo/sale_service_demo.xml',
    ],
    'installable': True,
    'auto_install': True,
}
