{
    "name": "Spreadsheet dashboard for sales",
    "version": "1.0",
    "category": "Productivity/Dashboard",
    "summary": "Spreadsheet",
    "description": "Spreadsheet",
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "spreadsheet_dashboard",
        "sale",
        "sale_team",
    ],
    "data": [
        "data/dashboards.xml",
    ],
    "auto_install": [
        "sale",
    ],
}
