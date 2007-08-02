{
    "name":"Board for manufacturing",
    "version":"1.0",
    "author":"Tiny",
    "category":"Board",
    "depends":[
        "board",
        "mrp",
        "stock",
        "report_mrp",


    ],
    "demo_xml":["board_manufacturing_demo.xml"],
    "update_xml":["board_manufacturing_view.xml"],
    "description": """
    This module creates a dashboards for Manufaturing that includes:
    * List of next production orders
    * List of deliveries (out packing)
    * Graph of workcenter load
    * List of procurement in exception
    """,
    "active":False,
    "installable":True,
}
