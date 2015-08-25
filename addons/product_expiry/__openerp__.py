# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name' : 'Products Expiration Date',
    'version' : '1.0',
    'category' : 'Specific Industry Applications',
    'depends' : ['stock'],
    'demo' : ['data/product_expiry_demo.xml'],
    'description': """
Track different dates on products and production lots.
======================================================

Following dates can be tracked:
-------------------------------
    - end of life
    - best before date
    - removal date
    - alert date

Also implements the removal strategy First Expiry First Out (FEFO) widely used, for example, in food industries.
""",
    'data': ['views/product_expiry_view.xml',
             'views/product_template_views.xml',
             'views/stock_quant_views.xml',
             'data/product_expiry_data.xml'],
    'auto_install': False,
    'installable': True,
}
