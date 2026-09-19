{
    "name": "Italy - E-invoicing",
    "version": "0.5",
    "category": "Accounting/Localizations/EDI",
    "description": """
E-invoice implementation
    """,
    "author": "Odoo S.A.",
    "website": "http://www.odoo.com/",
    "license": "LGPL-3",
    "depends": [
        "l10n_it",
        "account_edi_proxy_client",
        "account_debit_note",
    ],
    "external_dependencies": {
        "python": [
            "python-stdnum",
        ],
        "apt": {
            "python-stdnum": "python3-stdnum",
        },
    },
    "data": [
        "security/ir.model.access.csv",
        "data/account.account.tag.csv",
        "data/invoice_it_simplified_template.xml",
        "data/invoice_it_template.xml",
        "data/ir_cron.xml",
        "data/l10n_it.document.type.csv",
        "views/account_payment_method.xml",
        "views/account_tax_view.xml",
        "views/l10n_it_document_type.xml",
        "views/l10n_it_view.xml",
        "views/portal_address_templates.xml",
        "views/report_invoice.xml",
        "views/res_config_settings_views.xml",
        "views/l10n_it_edi_menus.xml",
    ],
    "demo": [
        "demo/account_invoice_demo.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "l10n_it_edi/static/src/interactions/**/*",
        ],
        "web.assets_tests": [
            "l10n_it_edi/static/tests/tours/*.js",
        ],
    },
    "auto_install": [
        "l10n_it",
    ],
    "post_init_hook": "_l10n_it_edi_post_init",
    "uninstall_hook": "uninstall_hook",
}
