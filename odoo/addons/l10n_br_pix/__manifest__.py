# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": "Brazil Pix QR codes",
    "countries": ["br"],
    "category": "Accounting/Localizations",
    "description": """
Implements Pix QR codes for Brazil.
""",
    "depends": [
        "l10n_br",
        "account_qr_code_emv",
    ],
    "data": ["views/res_bank_views.xml"],
    "license": "LGPL-3",
    "auto_install": True,
}
