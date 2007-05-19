{
	"name" : "Double-entry Inventory Management",
	"version" : "1.0",
	"author" : "Tiny",
	"website" : "http://tinyerp.com/module_stock.html",
	"depends" : ["product", "account"],
	"category" : "Generic Modules/Inventory Control",
	"init_xml" : [],
	"demo_xml" : [
#		"stock_demo.xml"
	],
	"update_xml" : ["stock_workflow.xml", "stock_data.xml", "stock_incoterms.xml","stock_wizard.xml", "stock_view.xml", "stock_report.xml", "stock_sequence.xml", "product_data.xml",],
	"active": False,
	"installable": True
}
