{
    "name": "Link Tracker",
    "version": "19.0.1.3",
    "category": "Marketing",
    "summary": "Shorten URLs and use them to track clicks and UTMs",
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "utm",
        "mail",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_cron.xml",
        "views/link_tracker_views.xml",
        "views/utm_campaign_views.xml",
        "views/link_tracker_menus.xml",
    ],
}
