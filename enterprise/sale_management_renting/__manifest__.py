# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Sale Management for Rental",
    'version': '1.0',
    'category': 'Hidden',
    'description': "This module adds management features to the sale renting app.",
    'depends': ['sale_renting', 'sale_management'],
    'data': [
        'views/sale_order_template_views.xml',
        'views/sale_order_views.xml',
        'views/sale_renting_menus.xml',
    ],
    'demo': [
        'data/rental_management_demo.xml',
    ],
    'auto_install': True,
    'license': 'OEEL-1',
}
