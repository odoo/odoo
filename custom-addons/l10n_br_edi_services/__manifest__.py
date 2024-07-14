# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": "Brazilian Accounting EDI for services",
    "version": "1.0",
    "description": """
Brazilian Accounting EDI
========================
Provides electronic invoicing for services for Brazil through Avatax.
""",
    "category": "Accounting/Localizations/EDI",
    "license": "OEEL-1",
    "depends": ["l10n_br_avatax_services", "l10n_br_edi"],
    "data": ["views/account_move_views.xml", "wizard/l10n_br_edi_invoice_update_views.xml", "data/ir_cron.xml"],
    "auto_install": True,
}
