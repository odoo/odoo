{
	"name" : "Sales Management - Reporting",
	"version" : "1.0",
	"author" : "Tiny",
	"website" : "http://tinyerp.com/module_sale.html",
	"depends" : ["sale"],
	"category" : "Generic Modules/Sales & Purchases",
	"description": """
	Reporting for the sale module:
	* Sales order by product (my/this month/all)
	* Sales order by category of product (my/this month/all)

	Some predefined lists:
	* Sales of the month
	* Open quotations
	* Uninvoiced Sales
	* Uninvoiced but shipped Sales
	""",
	"init_xml" : [],
	"demo_xml" : [],
	"update_xml" : ["report_sale_view.xml","report_sale_graph.xml"],
	"active": False,
	"installable": True
}
