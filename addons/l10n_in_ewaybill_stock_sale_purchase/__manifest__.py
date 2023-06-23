# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name": """E-waybill - Dropshipping""",
    "version": "1.0",
    'category': 'Accounting/Localizations',
    "depends": [
        "l10n_in_ewaybill_stock_sale",
        "l10n_in_ewaybill_stock_purchase",
        "l10n_in_ewaybill_stock",
        "stock_dropshipping",
    ],
    "description": """Allows to set the tax and price on Stock Move and partner details on Ewaybill in case of Dropshipping""",
    'installable': True,
    'auto_install': True,
    "license": "LGPL-3",
}
