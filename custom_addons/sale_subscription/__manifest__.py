{
    "name": "Subscriptions",
    "version": "19.0.1.0.0",
    "summary": (
        "Recurring subscription management - "
        "Kore Tier 2 substitute for sale_subscription"
    ),
    "description": "Kore clean-room recurring subscription engine and invoicing workflow.",
    "category": "Sales/Subscriptions",
    "author": "Kore",
    "license": "LGPL-3",
    "depends": [
        "base",
        "mail",
        "product",
        "sale",
        "sale_management",
        "analytic",
        "account",
    ],
    "data": [
        "security/sale_subscription_groups.xml",
        "security/ir.model.access.csv",
        "data/sale_subscription_sequence.xml",
        "data/sale_subscription_stages.xml",
        "data/sale_subscription_close_reasons.xml",
        "data/sale_subscription_cron.xml",
        "views/sale_subscription_stage_views.xml",
        "views/sale_subscription_template_views.xml",
        "views/sale_subscription_views.xml",
        "views/sale_subscription_menus.xml",
        "views/res_partner_views.xml",
    ],
    "installable": True,
    "application": True,
    # Traceability - see SOURCES.md
    # Architecture informed by: OCA/contract/subscription_oca (AGPL-3, ref only)
    #                           OCA/contract/contract (LGPL-3/AGPL-3, ref only)
}

