{
    "name": "OD19 Sales Contract Core",
    "author": "OD19",
    "version": "19.0.1.1.0",
    "depends": [
        "sale_management",
        "mail",
        "od19_sales_project_context",
        # Owns ``project.project.od19_project_type`` (NOT NULL). Without this
        # dependency we load (and run our tests) before that module, so the
        # field is unregistered and creating a project violates the not-null
        # constraint.
        "od19_project_document_sequence",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/sales_contract_views.xml",
        "views/sale_order_views.xml",
    ],
    "installable": True,
    "license": "LGPL-3",
    "icon": "/od19_sales_contract_core/static/description/icon.svg",
}
