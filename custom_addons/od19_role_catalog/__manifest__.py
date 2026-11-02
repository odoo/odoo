{
    "name": "OD19 Role Catalog (Business Roles)",
    "author": "OD19",
    "version": "19.0.1.0.0",
    "category": "Administration",
    "summary": "Business role definitions (~43 res.users.role) grouped under the OD19 Roles privilege",
    "description": """
OD19 Role Catalog (Business Roles)
==================================

Layer 2 of the OD19 access-control architecture. This module contains **data
only**: it declares the business roles of Auto-Info as ``res.users.role``
records and binds each one to the groups that already exist in the core, OCA
and OD19 business modules.

Because it references groups coming from every business module, it must be
installed **last** (after all domain modules and after ``od19_security_roles``).

Contents
--------

* Family A/B/C — Governance, Sales, Purchase (``od19_roles_governance.xml``).
* Family D/E/F — Inventory, Accounting, Service (``od19_roles_operations.xml``).
* Family G/H/I/J — HR, ISO, Reporting, Support (``od19_roles_backoffice.xml``).

Roles are ``noupdate="1"`` records: administrators may retune them in the UI
without the next module upgrade overwriting their changes.
""",
    "depends": [
        "base",
        "base_user_role",
        "od19_security_roles",
        # Odoo core / standard apps
        "sales_team",
        "project",
        "purchase",
        "stock",
        "account",
        "hr",
        "hr_attendance",
        "fleet",
        # OCA
        "stock_request",
        "document_knowledge",
        "helpdesk_mgmt",
        # OD19 business modules that own the referenced groups
        "od19_currency_rate_bot",
        "od19_dashboard",
        "od19_document_sign",
        "od19_helpdesk_extension",
        "od19_meeting_room_booking",
        "od19_purchase_procurement_core",
        "od19_sales_customer_risk_gate",
        "od19_sales_oca_bridge_workflow",
    ],
    "data": [
        "data/od19_roles_governance.xml",
        "data/od19_roles_operations.xml",
        "data/od19_roles_backoffice.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
    "license": "LGPL-3",
    "icon": "/od19_role_catalog/static/description/icon.svg",
}
