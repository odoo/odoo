{
    "name": "Internal Issue Management",
    "version": "19.0.1.0.0",
    "category": "Internal Operations",
    "summary": "Internal issue reporting with privacy controls and tier validation",
    "description": """
Internal Issue Management
=========================
Extends OCA helpdesk_mgmt with:
- Privacy controls (public / department / private)
- Emergency flag and priority
- Tier validation for escalation
- Multi-channel notifications on assignment/update
- Resolution tracking for knowledge base conversion
""",
    "author": "OD19",
    "website": "https://github.com/odoo/odoo",
    "license": "LGPL-3",
    "depends": [
        "helpdesk_mgmt",
        "base_tier_validation",
        "hr",
        "mail",
        "od19_notification_multi_channel",
        "od19_security_roles",
    ],
    "data": [
        "security/internal_issue_security.xml",
        "security/ir.model.access.csv",
        "security/od19_department_rule.xml",
        "data/internal_issue_data.xml",
        "views/helpdesk_ticket_views.xml",
        "views/helpdesk_ticket_category_views.xml",
        "views/internal_issue_menus.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
    "icon": "/od19_internal_issue/static/description/icon.svg",
}
