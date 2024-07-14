# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": "Brazilian Accounting EDI For Sale",
    "version": "1.0",
    "description": """
Brazilian Accounting EDI for Sale
=================================
Adds some fields to sale orders that will be carried over the invoice.
""",
    "category": "Accounting/Localizations/EDI",
    "license": "OEEL-1",
    "depends": ["sale_external_tax", "l10n_br_edi"],
    "data": [
        "views/sale_order_views.xml",
    ],
    "auto_install": True,
}
