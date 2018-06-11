# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name' : 'Products Expiration Date',
    'category' : 'Warehouse',
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
    'data': [
        'security/stock_security.xml',

        'views/production_lot_views.xml',
        'views/product_template_views.xml',
        'views/res_config_settings_views.xml',
        'views/res_users_views.xml',
        'views/stock_quant_views.xml',

        'data/product_expiry_data.xml',
    ],
}
