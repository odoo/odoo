# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Purchase Repair',
    'summary': 'Keep track of linked purchase and repair orders',
    'version': '1.0',
    'category': 'Repair/Purchase',
    'license': 'LGPL-3',
    'depends': ['repair', 'purchase'],
    'data': [
        'views/purchase_views.xml',
        'views/repair_views.xml',
    ],
    'auto_install': True,
    'installable': True,
}
