{
	"name" : "Sales Management",
	"version" : "1.0",
	"author" : "Tiny",
	"website" : "http://tinyerp.com/module_sale.html",
	"depends" : ["product", "stock", "mrp"],
	"category" : "Generic Modules/Sales & Purchases",
	"init_xml" : [],
	"demo_xml" : ["sale_demo.xml"],
	"update_xml" : [
		"sale_workflow.xml",
		"sale_sequence.xml",
		"sale_data.xml",
		"sale_view.xml",
		"sale_report.xml",
		"sale_wizard.xml",
		"stock_view.xml"
	],
	"active": False,
	"installable": True
}
