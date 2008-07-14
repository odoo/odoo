{
    "name" : "Enterprise Processus",
    "version" : "1.0",
    "author" : "Tiny",
    "website" : "http://tinyerp.com",
    "category" : "Generic Modules/Base",
    "description": """
This module allows you to manage your processus for the end-users.
    """,
    "depends" : ["base"],
    "init_xml" : [],
    "demo_xml" : [],
    "update_xml" : [
        'processus_view.xml',
        'ir.model.access.csv'],
    "active": False,
    "installable": True
}
