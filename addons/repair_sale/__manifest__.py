# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Repairs and Sale Management',
    'category': 'Supply Chain/Inventory',
    'summary': 'Create Sale quotations and invoices through repairs',
    'depends': ['repair', 'sale_stock', 'sale_management'],
    'auto_install': True,
    'data': [
        'views/product_views.xml',
        'views/repair_views.xml',
        'views/sale_order_views.xml',
        'views/account_move_views.xml',
    ],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
