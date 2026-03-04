{
    "name": "Sign",
    "version": "19.0.1.0.0",
    "summary": (
        "Electronic document signing - "
        "Kore Tier 2 substitute for sign"
    ),
    "description": "Kore clean-room document signature requests and signer workflow.",
    "category": "Productivity/Sign",
    "author": "Kore",
    "license": "LGPL-3",
    "depends": [
        "base",
        "mail",
        "portal",
        "web",
        "base_setup",
        "sale_subscription",
    ],
    "data": [
        "security/sign_groups.xml",
        "security/sign_rules.xml",
        "security/ir.model.access.csv",
        "data/sign_sequence.xml",
        "data/sign_item_type_data.xml",
        "data/sign_cron.xml",
        "views/sign_item_type_views.xml",
        "views/sign_template_views.xml",
        "views/sign_request_views.xml",
        "views/sign_send_request_wizard_views.xml",
        "views/sign_menus.xml",
    ],
    "installable": True,
    "application": True,
    # Traceability - see SOURCES.md
    # Architecture informed by: OCA/sign/sign_oca (AGPL-3, reference only)
    #                           Odoo Enterprise sign public API contract
}

