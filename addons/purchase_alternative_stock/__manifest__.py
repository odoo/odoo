# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Purchase Alternative Stock',
    'version': '1.2',
    'category': 'Supply Chain/Purchase',
    'sequence': 70,
    'depends': ['purchase_alternative', 'purchase_stock'],
    'data': [
        'views/purchase_views.xml',
    ],
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
