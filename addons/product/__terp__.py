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

	Products support variants, different pricing methods, suppliers
	information, make to stock/order, different unit of measures,
	packagins and properties.

	Pricelists supports:
	* Multiple-level of discount (by product, category, quantities)
	* Compute price based on different criterions:
		* Other pricelist,
		* Cost price,
		* List price,
		* Supplier price, ...
	Pricelists preferences by product and/or partners.

	Print product labels with barcodes.
	""",
	"update_xml" : ["product_data.xml","product_report.xml",
		"product_view.xml", "pricelist_view.xml","product_security.xml"],
	"active": False,
	"installable": True
}
