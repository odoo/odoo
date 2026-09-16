{
    "name": "Fleet History",
    "version": "2.1",
    "category": "Human Resources",
    "summary": "Get history of driven cars by employees",
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "fleet",
        "resource_asset_hr",
    ],
    "data": [
        "views/employee_views.xml",
        "views/fleet_vehicle_views.xml",
        "wizards/hr_departure_wizard_views.xml",
        "data/hr_fleet_data.xml",
    ],
    "demo": [
        "demo/hr_fleet_demo.xml",
    ],
    "auto_install": True,
}
