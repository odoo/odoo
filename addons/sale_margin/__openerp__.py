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
    'author':'OpenERP SA',
    'depends':['sale'],
    'demo':['sale_margin_demo.xml'],
    'test': ['test/sale_margin.yml'],
    'data':['security/ir.model.access.csv','sale_margin_view.xml'],
    'auto_install': False,
    'installable': True,
}
