#
# Use the custom module to put your specific code in a separate module.
#
{
    "name" : "Suport for iCal based on Document Management System",
    "version" : "1.0",
    "author" : "Tiny",
    "category" : "Generic Modules/Others",
    "website": "http://www.tinyerp.com",
    "description": """Allows to synchronize calendars with others applications.""",
    "depends" : ["document","crm_configuration"],
    "init_xml" : ["document_data.xml"],
    "update_xml" : [
        "document_view.xml",
        "security/ir.model.access.csv",
    ],
    "demo_xml" : [
        "document_demo.xml"
    ],
    "active": False,
    "installable": True
}
