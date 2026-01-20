# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "POS - Product Expiry",
    'category': "Technical",
    'summary': 'Link module between Point of Sale and Product Expiry',
    'depends': ['point_of_sale', 'product_expiry'],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_product_expiry/static/src/app/services/*.js',
        ],
    },
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
