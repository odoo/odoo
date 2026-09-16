{
    "name": "Maintenance - HR",
    "version": "1.3",
    "category": "Human Resources",
    "sequence": 125,
    "summary": "Maintenance orders raised by employees",
    "description": """
Bridge between HR and Maintenance.""",
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "maintenance",
        "resource_asset_hr",
    ],
    "data": [
        "security/equipment.xml",
        "views/maintenance_views.xml",
    ],
    "auto_install": True,
}
