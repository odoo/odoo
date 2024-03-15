{
    "license": "LGPL-3",
    "name": "Employee Punishment",
    "version": "1.0",
    "depends": ["base"],
    "author": "John Smith",
    "category": "",
    "description": """
    Description text
    """,
    # # data files always loaded at installation
    "data": [
        "ir.model.access.csv",
        "views/estate_property_views.xml",
        "views/estate_menu.xml",
    ],
    # # data files containing optionally loaded demonstration data
    # 'demo': [
    #     'demo/demo_data.xml',
    # ],
    "installable": True,
    "auto_install": False,
    "application": True,
}
