#
# Use the custom module to put your specific code in a separate module.
#
{
    "name" : "Integrated Document Management System",
    "version" : "1.0",
    "author" : "Tiny",
    "category" : "Generic Modules/Others",
    "website": "http://www.tinyerp.com",
    "description": """This is a complete document management system:
    * FTP Interface
    * User Authentification
    * Document Indexation
""",
    "depends" : ["base"],
    "init_xml" : ["document_data.xml"],
    "update_xml" : [
        "document_view.xml",
        "security/document_security.xml",
        "security/ir.model.access.csv",
    ],
    "demo_xml" : ["document_demo.xml"],
    "active": False,
    "installable": True
}
