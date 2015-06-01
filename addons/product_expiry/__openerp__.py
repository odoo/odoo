# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name' : 'Products Expiry Date',
    'version' : '1.0',
    'author' : 'OpenERP SA',
    'category' : 'Specific Industry Applications',
    'website': 'https://www.odoo.com',
    'depends' : ['stock'],
    'demo' : ['product_expiry_demo.xml'],
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
    'data' : ['product_expiry_view.xml', 'product_expiry_data.xml'],
    'auto_install': False,
    'installable': True,
}
