{
	"name" : "Purchase Management",
	"version" : "1.0",
	"author" : "Tiny",
	"website" : "http://tinyerp.com/module_purchase.html",
	"depends" : ["base", "account", "stock"],
	"category" : "Generic Modules/Sales & Purchases",
	"init_xml" : [],
	"demo_xml" : ["purchase_demo.xml", 
				  #"purchase_unit_test.xml"
				  ],
	"update_xml" : [
		"purchase_workflow.xml", 
		"purchase_sequence.xml", 
		"purchase_data.xml", 
		"purchase_view.xml", 
		"purchase_report.xml", 
		"purchase_wizard.xml",
		"stock_view.xml",
		"purchase_security.xml"
	],
	"active": False,
	"installable": True
}
