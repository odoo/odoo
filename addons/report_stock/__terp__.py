{
	"name" : "Stock report",
	"version" : "1.0",
	"author" : "Tiny",
	"website" : "http://tinyerp.com/",
	"depends" : ["stock", "product",],
	"category" : "Generic Modules/Inventory Control",
	"description" : """
	This module adds new reports based on the stock module.

	It create a new menu to get products by production lots within
	the different locations:
		Inventory Control/Reporting/Traceability/Stock by production lots
	""",
	"init_xml" : [],
	"demo_xml" : [],
	"update_xml" : ["report_stock_view.xml",],
	"active": False,
	"installable": True
}
