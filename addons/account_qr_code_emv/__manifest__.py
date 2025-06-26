# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'account_qr_code_emv',
    'category': 'Accounting/Payment',
    'version': '1.0',
    'description': """
Bridge module addings support for EMV Merchant-Presented QR-code generation for Payment System.
    """,
    'author': 'Odoo SA',
    'depends': ['account'],
    'data': [
        'views/res_bank_views.xml',
    ],
    'license': 'LGPL-3',
}
