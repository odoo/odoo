{
	"name" : "Products & Pricelists",
	"version" : "1.0",
	"author" : "Tiny",
	"category" : "Generic Modules/Inventory Control",
	"depends" : ["base"],
	"init_xml" : [],
	"demo_xml" : ["product_demo.xml"],
	"description": """
	This is the base module to manage products and pricelists in Tiny ERP.

	To detail: products
	To detail: pricelists

	Reports: ...
	""",
	"update_xml" : ["product_data.xml","product_report.xml", "product_wizard.xml","product_view.xml", "pricelist_view.xml"],
	"active": False,
	"installable": True
}
