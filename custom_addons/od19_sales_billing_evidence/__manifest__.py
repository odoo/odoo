{
    "name": "OD19 Sales Billing Evidence",
    "author": "OD19",
    "version": "19.0.1.1.0",
    "depends": ["sale_management", "od19_sales_project_context", "od19_sales_contract_core"],
    "data": [
        "security/ir.model.access.csv",
        "views/billing_evidence_views.xml",
        "views/sale_order_views.xml",
    ],
    "installable": True,
    "license": "LGPL-3",
    "icon": "/od19_sales_billing_evidence/static/description/icon.svg",
}
