{
    "name": "Solar Project",
    "version": "19.0.1.0.0",
    "summary": "Solar energy installation project management",
    "category": "Project",
    "depends": [
        "project",
        "sale_project",
        "project_purchase",
        "project_account",
        "crm",
        "stock",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/solar_document_type_data.xml",
        "views/project_project_views.xml",
        "views/solar_document_views.xml",
        "views/menus.xml",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
