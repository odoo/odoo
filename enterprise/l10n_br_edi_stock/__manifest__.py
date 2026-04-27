# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": "Brazilian Accounting EDI for stock",
    "version": "1.0",
    "description": """
Brazilian Accounting EDI for stock
==================================
Adds delivery-related information to the NF-e.
""",
    "category": "Accounting/Localizations/EDI",
    "license": "OEEL-1",
    "depends": [
        "l10n_br_edi",
        "sale_stock",  # move_ids on sale.order.line
    ],
    "data": [
        "views/account_move_views.xml",
        "views/stock_package_type_views.xml"
    ],
    "auto_install": True,
}
