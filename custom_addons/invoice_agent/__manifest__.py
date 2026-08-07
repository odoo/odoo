{
    "name": "Invoice Agent",
    "version": "19.0.0.5.0",
    "category": "Accounting/Accounting",
    "summary": "AI Extraction for account.move — queue, wizard, security, automations, cron",
    "depends": ["account", "sale", "base_automation"],
    "post_init_hook": "post_init_hook",
    "data": [
        "security/invoice_agent_groups.xml",
        "security/ir.model.access.csv",
        "security/invoice_agent_rules.xml",
        "views/account_move_views.xml",
        "views/res_partner_views.xml",
        "views/account_journal_views.xml",
        "views/invoice_agent_views.xml",
        "views/usage_views.xml",
        "views/res_config_settings_views.xml",
        "wizard/bulk_process_wizard_views.xml",
        "data/automation_data.xml",
        "data/cron.xml"
    ],
    "assets": {
        "web.assets_backend": [
            "invoice_agent/static/src/js/suggestion_panel.js",
            "invoice_agent/static/src/js/suggestion_panel.xml"
        ]
    },
    "installable": True,
    "application": False,
    "license": "LGPL-3"
}
