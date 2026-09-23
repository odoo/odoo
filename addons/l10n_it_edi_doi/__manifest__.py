{
    "name": "Italy - Declaration of Intent",
    "version": "0.2",
    "category": "Accounting/Localizations",
    "description": """
    Add support for the Declaration of Intent (Dichiarazione di Intento) to the Italian localization.
    """,
    "author": "Odoo S.A.",
    "website": "https://www.odoo.com/documentation/latest/applications/finance/fiscal_localizations/italy.html",
    "license": "LGPL-3",
    "depends": [
        "l10n_it_edi",
        "sale",
    ],
    "countries": [
        "it",
    ],
    "data": [
        "security/ir.access.csv",
        "data/invoice_it_template.xml",
        "views/l10n_it_edi_doi_declaration_of_intent_views.xml",
        "views/account_move_views.xml",
        "views/report_invoice.xml",
        "views/res_partner_views.xml",
        "views/sale_ir_actions_report_templates.xml",
        "views/sale_order_views.xml",
    ],
    "post_init_hook": "_l10n_it_edi_doi_post_init",
}
