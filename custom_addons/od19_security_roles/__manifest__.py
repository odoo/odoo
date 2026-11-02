{
    "name": "OD19 Security Roles (Access Control Layer)",
    "author": "OD19",
    "version": "19.0.1.1.0",
    "category": "Administration",
    "summary": "Central access-control layer: role privilege, department scope groups and employee-to-user department mirror",
    "description": """
OD19 Security Roles (Access Control Layer)
==========================================

Layer 1 of the OD19 access-control architecture. This module deliberately
knows nothing about business modules, so it can be installed before any
domain module without creating a circular dependency.

Contents
--------

* The ``OD19 Roles`` privilege used to group every OD19 business role.
* Four central groups: department scope, all-departments visibility,
  role manager and credit approver.
* ``res.users.od19_department_id`` (stored mirror of the employee
  department) so department-based record rules can be written safely.
* A daily cron repairing the department mirror.

Business roles themselves live in ``od19_role_catalog`` (Layer 2).
""",
    "depends": [
        "base",
        "base_user_role",
        "hr",
    ],
    "data": [
        "data/od19_security_role_privilege.xml",
        "security/od19_security_groups.xml",
        "security/ir.model.access.csv",
        "views/res_users_views.xml",
        "data/ir_cron_data.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
    "license": "LGPL-3",
    "icon": "/od19_security_roles/static/description/icon.svg",
}
