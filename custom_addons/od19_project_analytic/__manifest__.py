{
    "name": "OD19 Project & Analytic Accounting",
    "author": "OD19",
    "version": "19.0.1.0.0",
    "category": "Services/Project",
    "summary": "Extend standard project.project with Job Number, owning department, Project Owner, Contractors, and auto analytic account",
    "depends": [
        "project",
        "hr",
        "od19_contacts_partner_roles",
        "od19_security_roles",
        "purchase_stock",
    ],
    "data": [
        "security/od19_department_rule.xml",
        "views/project_project_views.xml",
    ],
    "installable": True,
    "license": "LGPL-3",
    "icon": "/od19_project_analytic/static/description/icon.svg",
}
