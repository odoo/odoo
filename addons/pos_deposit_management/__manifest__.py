# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Point of Sale - Deposit Management',
    'category': 'Sales/Point Of Sale',
    'summary': 'Add deposit lines for products in the Point of Sale',
    'depends': ['point_of_sale'],
    'data': [
        'views/product_views.xml',
        'receipt/pos_order_receipt.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_deposit_management/static/src/**/*',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
    'uninstall_hook': 'uninstall_hook',
}
