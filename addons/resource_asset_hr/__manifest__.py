{
    "name": "Assets - HR",
    "version": "1.0",
    "category": "Human Resources",
    "summary": "Who holds an asset, named by employee",
    "description": """
Names an asset's operator and manager by employee rather than by resource, for the HR views that
speak of people as employees. The custody itself stays the assignment on the asset's resource.
""",
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "hr",
        "resource_asset",
    ],
    "data": [
        "views/resource_asset_views.xml",
        "views/hr_views.xml",
        "wizards/hr_departure_wizard_views.xml",
    ],
    "auto_install": True,
}
