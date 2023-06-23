# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name": """E-waybill - Purchase""",
    "version": "1.0",
    'category': 'Accounting/Localizations/Purchase',
    "depends": [
        "purchase",
        "l10n_in_ewaybill_stock",
    ],
    "description": """Allows to set the tax and price on Stock Move and partner details on Ewaybill according to Purchase Order""",
    'installable': True,
    'auto_install': True,
    "license": "LGPL-3",
}
