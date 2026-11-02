{
    "name": "Asset Loan Management",
    "version": "19.0.1.0.0",
    "category": "Internal Operations",
    "summary": "Tool/equipment loan management on top of maintenance + assets",
    "description": """
Asset Loan Management
=====================
Manage internal tool/equipment loans:
- Loan documents (borrower, dates, status)
- Loan lines linked to maintenance.equipment
- Calibration tracking via equipment next_action_date
- Multi-channel notifications for due / overdue / calibration
""",
    "author": "OD19",
    "website": "https://github.com/odoo/odoo",
    "license": "LGPL-3",
    "depends": [
        "maintenance",
        "mail",
        "account_asset_management",
        "od19_notification_multi_channel",
    ],
    "data": [
        "security/asset_loan_security.xml",
        "security/ir.model.access.csv",
        "data/asset_loan_sequence.xml",
        "data/asset_loan_cron.xml",
        "views/asset_loan_views.xml",
        "views/asset_loan_line_views.xml",
        "views/maintenance_equipment_views.xml",
        "views/asset_loan_menus.xml",
        "reports/asset_loan_report.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
    "icon": "/od19_asset_loan/static/description/icon.svg",
}
