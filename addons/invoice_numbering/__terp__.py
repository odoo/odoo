{
    "name" : "Invoice Numbering",
    "version" : "1.0",
    "author" : "Tiny",
    "category" : "Generic Modules/Accounting",
    "website" : "http://tinyerp.com/module_invoice_numbering.html",
    "description": """
    This Module handles the Invoice sequences so that the invoices made in the new year(i.e. January onwards)
    will have the predefined sequences. 
    """,
    "depends" : ["base","account"],
    "init_xml" : [],
    "demo_xml" : [],
    "update_xml" : [
        "invoice_numbering_view.xml", 
    ],
    "active": False,
    "installable": True
}
