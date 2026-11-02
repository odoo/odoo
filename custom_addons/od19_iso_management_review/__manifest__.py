{
    "name": "ISO Management Review",
    "version": "19.0.1.0.0",
    "category": "Management/ISO",
    "summary": "ISO 9001 / ISO 14001 Management Review Meeting",
    "author": "TRAE",
    "license": "LGPL-3",
    "depends": ["od19_iso_document_control", "od19_iso_internal_audit", "od19_iso_nonconformity", "hr"],
    "data": [
        "security/ir.model.access.csv",
        "data/management_review_data.xml",
        "views/management_review_views.xml",
        "views/menu.xml",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
    "icon": "/od19_iso_management_review/static/description/icon.svg",
}
