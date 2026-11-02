{
    "name": "OD19 Sales Reporting",
    "author": "OD19",
    "version": "19.0.1.0.0",
    "depends": ["od19_sales_project_context", "od19_sales_contract_core", "od19_sales_billing_evidence"],
    "data": [
        "security/ir.model.access.csv",
        "security/sales_reporting_security.xml",
        "views/report_sales_project_revenue_views.xml",
        "views/report_repeat_business_views.xml",
    ],
    "installable": True,
    "license": "LGPL-3",
    "icon": "/od19_sales_reporting/static/description/icon.svg",
}
