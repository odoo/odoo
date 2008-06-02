{
	"name" : "Sales Management",
	"version" : "1.0",
	"author" : "Tiny",
	"website" : "http://tinyerp.com/module_sale.html",
	"depends" : ["product", "stock", "mrp"],
	"category" : "Generic Modules/Sales & Purchases",
	"init_xml" : [],
	"demo_xml" : ["sale_demo.xml", "sale_unit_test.xml"],
	"description": """
	The base module to manage quotations and sales orders.

	* Workflow with validation steps:
		- Quotation -> Sale order -> Invoice
	* Invoicing methods:
		- Invoice on order (before or after shipping)
		- Invoice on delivery
		- Invoice on timesheets
		- Advance invoice
	* Partners preferences (shipping, invoicing, incoterm, ...)
	* Products stocks and prices
	* Delivery methods:
		- all at once, multi-parcel
		- delivery costs
	""",
	"update_xml" : [

		"sale_workflow.xml",
		"sale_sequence.xml",
		"sale_data.xml",
		"sale_wizard.xml",
		"sale_view.xml",
		"sale_report.xml",
		"sale_wizard.xml",
		"stock_view.xml",
		"sale_security.xml"
	],
	"active": False,
	"installable": True
}
