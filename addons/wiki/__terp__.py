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
    "demo_xml" : [
        "data/wiki_faq.xml",
    ],
    "update_xml" : [
        "wiki_view.xml",
        "data/wiki_main.xml",
        "data/wiki_quickstart.xml",
        "wizard/wizard_view.xml",
        "security/ir.model.access.csv"
    ],
    "active": False,
    "installable": True
}
