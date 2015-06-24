# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Margins in Sales Orders',
    'version':'1.0',
    'category' : 'Sales Management',
    'description': """
This module adds the 'Margin' on sales order.
=============================================

This gives the profitability by calculating the difference between the Unit
Price and Cost Price.
    """,
    'author':'Odoo S.A.',
    'depends':['sale'],
    'demo':['data/sale_order_demo.xml'],
    'data':['security/ir.model.access.csv','views/inherited_sale_order_views.xml'],
    'installable': True,
}
