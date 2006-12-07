#
# Use the custom module to put your specific code in a separate module.
#
{
	"name" : "Managing sales and deliveries by journal",
	"version" : "1.0",
	"author" : "Tiny",
	"category" : "Generic Modules/Sales & Purchases",
	"website": "http://www.tinyerp.com",
	"depends" : ["stock","sale"],
	"demo_xml" : ['sale_journal_demo.xml'],
	"init_xml" : ['sale_journal_data.xml'],
	"update_xml" : ["sale_journal_view.xml","picking_journal_view.xml","picking_journal_view_report.xml"],
	"active": False,
	"installable": True
}
