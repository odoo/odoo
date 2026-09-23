{
    "name": "Malaysia - E-invoicing",
    "version": "1.1",
    "category": "Accounting/Localizations/EDI",
    "summary": "E-invoicing using MyInvois",
    "description": """
    This modules allows the user to send their invoices to the MyInvois system.
    """,
    "author": "Odoo S.A.",
    "icon": "/account/static/description/l10n.png",
    "license": "LGPL-3",
    "depends": [
        "l10n_my",
        "l10n_my_ubl_pint",
        "account_edi_proxy_client",
    ],
    "countries": [
        "my",
    ],
    "data": [
        "data/ir_cron.xml",
        "data/l10n_my_edi.industry_classification.csv",
        "security/ir.access.csv",
        "views/account_move_view.xml",
        "views/account_tax_view.xml",
        "views/l10n_my_edi_industrial_classification_views.xml",
        "views/myinvois_document_views.xml",
        "views/product_template_view.xml",
        "views/report_invoice.xml",
        "views/res_company_view.xml",
        "views/res_config_settings_view.xml",
        "views/res_partner_view.xml",
        "views/account_portal_templates.xml",
        "wizards/myinvois_consolidate_invoice_wizard.xml",
        "wizards/myinvois_document_status_update_wizard.xml",
    ],
}
