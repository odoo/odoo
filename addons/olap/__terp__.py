{
    "name" : "Olap Schemes Management",
    "version" : "0.1",
    "author" : "Tiny",
    "website" : "http://www.openerp.com",
    "depends" : ["base"],
    "category" : "Generic Modules/Olap",
    "description": """
    Olap module is used to install BI module in client. Olap provides Online
    Analytical Process with the mdx query. BI provides Cube Browsing and
    Cube Designing. After installing Olap Module you will get Cube Browser
    and Cube Desinger in Reporting Menu. Cube Browser is used to generate
    the reports with table view (mdx view) of mdx query. and Cube designer
    is used to make cubes in BI..
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
