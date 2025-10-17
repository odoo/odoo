# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Manufacturing Expiry',
    'category': 'Supply Chain/Manufacturing',
    'summary': 'Manufacturing Expiry',
    'description': """
Technical module.
    """,
    'depends': ['mrp', 'product_expiry'],
    'data': [
        'wizard/confirm_expiry_view.xml',
    ],
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
