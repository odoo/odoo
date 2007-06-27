{
	"name" : "Carriers and deliveries",
	"version" : "1.0",
	"author" : "Tiny",
	"category" : "Generic Modules/Sales & Purchases",
	"description": "Allows to add delivery methods in sales order and packings. You can define your own carrier and delivery grids for prices. When creating invoices from pickings, Tiny ERP is able to add and compute the shipping line.",
	"depends" : ["sale","purchase", "stock",],
	"init_xml" : ["delivery_data.xml"],
	"demo_xml" : ["delivery_demo.xml"],
	"update_xml" : ["delivery_view.xml","delivery_wizard.xml"],
	"active": False,
	"installable": True,
}
