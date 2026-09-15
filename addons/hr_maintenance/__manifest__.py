{
    "name": "Maintenance - HR",
    "version": "1.2",
    "category": "Human Resources",
    "sequence": 125,
    "summary": "Asset custody for employees and departments, maintenance requesters",
    "description": """
Bridge between HR and Maintenance.""",
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "hr",
        "maintenance",
    ],
    "data": [
        "security/equipment.xml",
        "views/maintenance_views.xml",
        "views/hr_views.xml",
        "wizards/hr_departure_wizard_views.xml",
    ],
    "auto_install": True,
}
