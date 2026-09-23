{
    "name": "Event CRM",
    "version": "1.0",
    "category": "Marketing/Events",
    "description": "Create leads from event registrations.",
    "author": "Odoo S.A.",
    "website": "https://www.odoo.com/app/events",
    "license": "LGPL-3",
    "depends": [
        "event",
        "crm",
    ],
    "data": [
        "security/ir.access.csv",
        "data/crm_lead_merge_template.xml",
        "data/ir_action_data.xml",
        "data/ir_cron_data.xml",
        "views/crm_lead_views.xml",
        "views/event_registration_views.xml",
        "views/event_lead_rule_views.xml",
        "views/event_event_views.xml",
        "views/event_question_views.xml",
        "views/event_crm_menus.xml",
    ],
    "demo": [
        "demo/event_crm_demo.xml",
    ],
    "assets": {
        "web.assets_tests": [
            "event_crm/static/tests/tours/*.js",
        ],
    },
    "auto_install": True,
}
