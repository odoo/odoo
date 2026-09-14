{
    "name": "Peppol",
    "version": "1.3",
    "category": "Accounting/Accounting",
    "summary": "This module is used to send/receive documents with PEPPOL",
    "description": """
- Register as a PEPPOL participant
- Send and receive documents via PEPPOL network in Peppol BIS Billing 3.0 format
    """,
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "credential",
        "account_edi_proxy_client",
        "account_edi_ubl_cii",
    ],
    "external_dependencies": {
        "python": [
            "phonenumbers",
            "python-stdnum",
        ],
        "apt": {
            "phonenumbers": "python3-phonenumbers",
            "python-stdnum": "python3-stdnum",
        },
    },
    "countries": [
        "at",
        "be",
        "ch",
        "cy",
        "cz",
        "de",
        "dk",
        "ee",
        "es",
        "fi",
        "fr",
        "gr",
        "ie",
        "is",
        "it",
        "lt",
        "lu",
        "lv",
        "mt",
        "nl",
        "no",
        "pl",
        "pt",
        "ro",
        "se",
        "si",
    ],
    "data": [
        "data/cron.xml",
        "data/mail_templates_email_layouts.xml",
        "data/res_partner_data.xml",
        "security/ir.model.access.csv",
        "views/account_move_views.xml",
        "views/account_portal_templates.xml",
        "views/peppol_authentication_views.xml",
        "views/res_partner_views.xml",
        "views/res_config_settings_views.xml",
        "wizards/peppol_registration_views.xml",
        "wizards/peppol_config_wizard.xml",
    ],
    "demo": [
        "demo/account_peppol_demo.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "account_peppol/static/src/components/**/*",
            "account_peppol/static/src/css/**/*",
        ],
        "web.assets_frontend": [
            "account_peppol/static/src/interactions/*",
        ],
    },
    "auto_install": [
        "account_edi_ubl_cii",
    ],
    "post_init_hook": "_account_peppol_post_init",
}
