# -*- coding: utf-8 -*-

{
    'name' : 'Products Expiry Date',
    'version' : '1.0',
    'author' : 'Odoo S.A.',
    'category' : 'Specific Industry Applications',
    'website': 'https://www.odoo.com',
    'depends' : ['stock'],
    'demo' : ['data/product_product_demo.xml'],
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
    'data' : ['views/product_template_views.xml',
              'views/stock_production_lot_views.xml',
              'data/product_expiry_data.xml'],
    'installable': True,
}
