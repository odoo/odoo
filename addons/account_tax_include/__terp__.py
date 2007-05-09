{
	"name" : "Invoices and prices with taxes included",
	"version" : "1.0",
	"depends" : ["account"],
	"author" : "Tiny",
	"description": """Allow the user to work tax included prices.
Especially useful for b2c businesses.
	
This module implement the modification on the invoice form.
""",
	"website" : "http://tinyerp.com/module_account.html",
	"category" : "Generic Modules/Accounting",
	"init_xml" : [ ],
	"demo_xml" : [ ],
	"update_xml" : [ 'invoice_tax_incl.xml' ],
	"active": False,
	"installable": True
}
