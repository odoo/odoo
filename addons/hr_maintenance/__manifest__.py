{
    "name": "Maintenance - HR",
    "version": "1.1",
    "category": "Human Resources",
    "sequence": 125,
    "summary": "Equipment, Assets, Internal Hardware, Allocation Tracking",
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
