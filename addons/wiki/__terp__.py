{
    "name" : "Document Management - Wiki",
    "version" : "1.0",
    "author" : "Tiny",
    "description": """
    The base module to manage documents(wiki) 
    
    keep track for the wiki groups, pages, and history
    """,
    "category" : "Generic Modules/Others",
    "depends" : ["base"],
    "website" : "http://openerp.com",
    "init_xml" : [],
    "demo_xml" : [],
    "update_xml" : [
        "wiki_view.xml",
        #"wiki_data.xml",
        "wizard/wizard_view.xml",
        "security/ir.model.access.csv"
    ],
    "active": False,
    "installable": True
}
