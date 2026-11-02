{
    "name": "ISO Customer Satisfaction",
    "version": "19.0.1.0.0",
    "category": "Management/ISO",
    "summary": "ISO 9001 Customer Satisfaction Measurement and Surveys",
    "author": "TRAE",
    "license": "LGPL-3",
    "depends": ["od19_iso_document_control", "hr"],
    "data": [
        "security/ir.model.access.csv",
        "data/customer_satisfaction_data.xml",
        "views/customer_satisfaction_views.xml",
        "views/menu.xml",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
    "icon": "/od19_iso_customer_satisfaction/static/description/icon.svg",
}
