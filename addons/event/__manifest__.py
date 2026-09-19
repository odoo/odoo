{
    "name": "Events Organization",
    "version": "1.14",
    "category": "Marketing/Events",
    "summary": "Trainings, Conferences, Meetings, Exhibitions, Registrations",
    "description": """
Organization and management of Events.
======================================

The event module allows you to efficiently organize events and all related tasks: planning, registration tracking,
attendances, etc.

Key Features
------------
* Manage your Events and Registrations
* Use emails to automatically confirm and send acknowledgments for any event registration
""",
    "author": "Odoo S.A.",
    "website": "https://www.odoo.com/app/events",
    "license": "LGPL-3",
    "depends": [
        "credential",
        "barcodes",
        "mail",
        "phone_validation",
        "portal",
        "utm",
    ],
    "data": [
        "security/event_security.xml",
        "security/ir.model.access.csv",
        "views/event_ticket_views.xml",
        "views/event_mail_views.xml",
        "views/event_registration_views.xml",
        "views/event_slot_views.xml",
        "views/event_type_views.xml",
        "views/event_event_views.xml",
        "views/event_stage_views.xml",
        "reports/event_event_templates.xml",
        "reports/event_event_reports.xml",
        "reports/event_registration_report.xml",
        "data/ir_cron_data.xml",
        "data/mail_template_data.xml",
        "data/event_data.xml",
        "data/event_tour.xml",
        "views/res_config_settings_views.xml",
        "views/event_templates.xml",
        "views/res_partner_views.xml",
        "views/event_tag_views.xml",
        "views/event_question_views.xml",
        "views/event_registration_answer_views.xml",
        "data/event_question_data.xml",
        "views/event_menu_views.xml",
    ],
    "demo": [
        "demo/res_users_demo.xml",
        "demo/res_partner_demo.xml",
        "demo/event_demo_misc.xml",
        "demo/event_demo.xml",
        "demo/event_registration_demo.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "event/static/src/clickbot_entries.js",
            "event/static/src/client_action/**/*",
            "event/static/src/scss/event.scss",
            "event/static/src/event_state_selection_field/*",
            "event/static/src/icon_selection_field/icon_selection_field.js",
            "event/static/src/icon_selection_field/icon_selection_field.xml",
            "event/static/src/template_reference_field/*",
            "event/static/src/js/tours/**/*",
            "event/static/src/views/**/*",
        ],
        "web.assets_frontend": [
            "event/static/src/js/tours/**/*",
        ],
        "web.assets_unit_tests": [
            "event/static/tests/**/*.js",
        ],
        "web.report_assets_common": [
            "/event/static/src/scss/event_badge_report.scss",
            "/event/static/src/scss/event_full_page_ticket_report.scss",
            "/event/static/src/scss/event_full_page_ticket_responsive_html_report.scss",
        ],
        "web.report_assets_pdf": [
            "/event/static/src/scss/event_full_page_ticket_report_pdf.scss",
        ],
    },
}
