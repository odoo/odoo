# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'MTO Sale <-> Purchase',
    'category': 'Sales/Sales',
    'summary': 'SO/PO relation in case of MTO',
    'description': """
Add relation information between Sale Orders and Purchase Orders if Make to Order (MTO) is activated on one sold product.
""",
    'depends': ['sale_stock', 'purchase_stock', 'sale_purchase'],
    'data': [
        'views/purchase_order_views.xml',
    ],
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
