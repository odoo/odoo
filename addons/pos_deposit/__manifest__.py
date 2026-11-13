# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Point of Sale - Deposit',
    'category': 'Sales/Point Of Sale',
    'summary': 'Add deposit lines for products in the Point of Sale',
    'description': """

This module adds deposit management to the Point of Sale:
- Deposit Products: Allows you to set a deposit product for products sold in the POS.
- Automatic Deposits: Automatically adds the deposit product when the main product is added to the order.
- Combo Support: Supports deposits for combo products and their child products.
- Quantity Synchronization: Keeps deposit quantities in sync with the related products.
- Receipt Display: Displays deposit lines in the correct order on receipts.
""",
    'depends': ['point_of_sale'],
    'data': [
        'views/product_views.xml',
        'receipt/pos_order_receipt.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_deposit/static/src/**/*',
        ],
        'web.assets_unit_tests': [
            'pos_deposit/static/tests/unit/**/*',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
    'uninstall_hook': 'uninstall_hook',
}
