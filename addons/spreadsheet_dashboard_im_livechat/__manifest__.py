{
    "name": "Spreadsheet dashboard for live chat",
    "version": "1.0",
    "category": "Productivity/Dashboard",
    "summary": "Spreadsheet",
    "description": "Spreadsheet",
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "spreadsheet_dashboard",
        "im_livechat",
    ],
    "data": [
        "data/livechat_ongoing_sessions_actions.xml",
        "views/spreadsheet_dashboard_im_livechat_menus.xml",
        "data/dashboards.xml",
    ],
    "auto_install": [
        "im_livechat",
    ],
}
