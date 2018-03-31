# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Margins in Sales Orders',
    'version':'1.0',
    'category': 'Sales',
    'description': """
This module adds the 'Margin' on sales order.
=============================================

This gives the profitability by calculating the difference between the Unit
Price and Cost Price.
    """,
    'depends':['sale_management'],
    'demo':['data/sale_margin_demo.xml'],
    'data':['security/ir.model.access.csv','views/sale_margin_view.xml'],
}
