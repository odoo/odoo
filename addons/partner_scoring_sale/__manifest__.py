{
    "name": "Partner Scoring / Sales",
    "version": "19.0.1.0.0",
    "category": "Sales/Sales",
    "summary": "The customer's commercial tier on the order and in sales analysis",
    "description": """
An order carries the commercial tier its customer held when it was confirmed,
so a later reclassification does not rewrite what was sold to whom, and sales
analysis groups by it.
    """,
    "author": "AgroMarin",
    "website": "https://agromarin.mx",
    "license": "LGPL-3",
    "depends": [
        "partner_scoring",
        "sale",
    ],
    "data": [
        "views/sale_order_views.xml",
        "reports/sale_report_views.xml",
    ],
    "auto_install": True,
}
