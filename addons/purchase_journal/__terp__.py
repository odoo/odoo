#
# Use the custom module to put your specific code in a separate module.
#
{
	"name" : "Managing sales and deliveries by journal",
	"version" : "1.0",
	"author" : "Tiny",
	"category" : "Generic Modules/Sales & Purchases",
	"website": "http://www.tinyerp.com",
	"depends" : ["stock","purchase"],
	"demo_xml" : ['purchase_journal_demo.xml'],
	"init_xml" : ['purchase_journal_data.xml'],
	"update_xml" : ["purchase_journal_view.xml"],
	"active": False,
	"installable": True
}
