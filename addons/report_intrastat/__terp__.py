{
	"name" : "Intrastat Reporting - Reporting",
	"version" : "1.0",
	"author" : "Tiny",
	"website" : "http://tinyerp.com",
	"depends" : ["base", "product", "stock", "sale", "purchase"],
	"category" : "Generic Modules/Inventory Control",
	"description": "A module that adds intrastat reports.",
	"init_xml" : ["report_intrastat_data.xml",],
	"demo_xml" : [],
	"update_xml" : ["report_intrastat_view.xml",],
	"active": False,
	"installable": True
}
