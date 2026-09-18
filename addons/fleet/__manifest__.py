{
    "name": "Fleet",
    "version": "2.3",
    "category": "Human Resources/Fleet",
    "sequence": 185,
    "summary": "Manage your company's vehicles, drivers, services and costs",
    "description": """
Company fleet management
========================
A vehicle is an asset of kind vehicle: its model is a product with the manufacturer and
specifications, its drivers are driver assignments, its odometer is a meter, and its services
and costs are lines of the asset's ledger.

Main Features
-------------
* Register vehicles with plate, VIN, model and manufacturer
* Assign current and future drivers and apply the hand-over
* Record odometer readings
* Log services and analyse vehicle costs
""",
    "author": "Odoo S.A.",
    "website": "https://www.odoo.com/app/fleet",
    "license": "LGPL-3",
    "depends": [
        "mail",
        "resource_asset_product",
    ],
    "data": [
        "security/fleet_security.xml",
        "security/ir.model.access.csv",
        "data/fleet_cars_data.xml",
        "data/fleet_data.xml",
        "views/product_template_views.xml",
        "views/fleet_vehicle_views.xml",
        "views/fleet_service_views.xml",
        "wizards/fleet_vehicle_send_mail_views.xml",
        "views/fleet_menus.xml",
    ],
    "demo": [
        "demo/fleet_demo.xml",
    ],
    "application": True,
    "pre_init_hook": "pre_init_hook",
}
