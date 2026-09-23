{
    "name": "Event Exhibitors",
    "version": "1.2",
    "category": "Marketing/Events",
    "sequence": 1004,
    "summary": "Event: manage sponsors and exhibitors",
    "author": "Odoo S.A.",
    "website": "https://www.odoo.com/app/events",
    "license": "LGPL-3",
    "depends": [
        "website_event",
    ],
    "data": [
        "security/ir.access.csv",
        "data/event_sponsor_data.xml",
        "reports/website_event_exhibitor_reports.xml",
        "reports/website_event_exhibitor_templates.xml",
        "views/event_templates_sponsor.xml",
        "views/event_sponsor_views.xml",
        "views/event_event_views.xml",
        "views/event_exhibitor_templates_list.xml",
        "views/event_exhibitor_templates_page.xml",
        "views/event_type_views.xml",
        "views/event_menus.xml",
    ],
    "demo": [
        "demo/event_demo.xml",
        "demo/event_sponsor_demo.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "website_event_exhibitor/static/src/scss/event_templates_sponsor.scss",
            "website_event_exhibitor/static/src/scss/event_exhibitor_templates.scss",
            "website_event_exhibitor/static/src/interactions/**/*",
            "website_event_exhibitor/static/src/components/exhibitor_connect_closed_dialog/**/*",
        ],
        "web.report_assets_common": [
            "/website_event_exhibitor/static/src/scss/event_full_page_ticket_report.scss",
        ],
        "website.website_builder_assets": [
            "website_event_exhibitor/static/src/website_builder/**/*",
        ],
    },
}
