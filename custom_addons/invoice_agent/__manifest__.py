{
    "name": "Invoice Agent",
    "version": "19.0.0.7.0",
    "category": "Accounting/Accounting",
    "summary": "AI-powered vendor invoice extraction and validation — OCR, Claude structured output, RAG validation, confidence-based kanban routing",
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
        "views/queue_job_views.xml",
        "views/res_config_settings_views.xml",
        "wizard/bulk_process_wizard_views.xml",
        "data/automation_data.xml",
        "data/cron.xml",
        "data/queue_cron.xml"
    ],
    "assets": {
        "web.assets_backend": [
            "invoice_agent/static/src/js/suggestion_panel.js",
            "invoice_agent/static/src/js/suggestion_panel.xml",
            "invoice_agent/static/src/js/ai_status_widget.js"
        ]
    },
    "installable": True,
    "application": False,
    "license": "LGPL-3"
}
