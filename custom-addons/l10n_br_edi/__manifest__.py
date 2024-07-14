# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": "Brazilian Accounting EDI",
    "version": "1.0",
    "description": """
Brazilian Accounting EDI
========================
Provides electronic invoicing for Brazil through Avatax.
""",
    "category": "Accounting/Localizations/EDI",
    "license": "OEEL-1",
    "depends": ["l10n_br_avatax"],
    "data": [
        "data/res.country.csv",
        "data/mail_template_data.xml",
        "security/ir.model.access.csv",
        "views/account_move_view.xml",
        "views/res_country_views.xml",
        "wizard/account_move_send_views.xml",
        "wizard/l10n_br_edi_invoice_update_views.xml",
        "wizard/l10n_br_edi_cancel_range_views.xml",
    ],
}
