{
    "name" : "Olap Schemes Management",
    "version" : "0.1",
    "author" : "Tiny",
    "website" : "http://www.openerp.com",
    "depends" : ["base"],
    "category" : "Generic Modules/Olap",
    "description": """
    Base module to manage Olap schemas. Cube designer.
    """,
    "init_xml" :  ["data/olap_data.xml"],
    "update_xml" : [
        "data/olap_view.xml",
        "data/olap_wizard.xml",
        "data/olap_cube_view.xml",
        "data/olap_fact_view.xml",
        "data/olap_cube_workflow.xml",
        "data/olap_security.xml"
    ],
    "demo_xml" : ["data/olap_demo.xml"],
    "active": False,
    "installable": True
}
