# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Service Margin Estimation for Sales Orders',
    'version': '1.0',
    'summary': 'Obtain an estimate of your margin for services on your sales orders',
    'description': """
Allows to compute accurate margin for Service sales.
======================================================
""",
    'category': 'Services/Sales',
    'depends': ['sale_margin', 'sale_timesheet'],
    'auto_install': True,
    'license': 'LGPL-3',
}
