{
	"name" : "Manufacturing Resource Planning",
	"version" : "1.0",
	"author" : "Tiny",
	"website" : "http://tinyerp.com/module_mrp.html",
	"category" : "Generic Modules/Production",
	"depends" : ["stock", "hr", "purchase", "product"],
	"description": """
	This is the base module to manage the manufacturing process in Tiny ERP.

	Features:
	* Make to Stock / Make to Order (by line)
	* Multi-level BoMs, no limit
	* Multi-level routing, no limit
	* Routing and workcenter integrated with analytic accounting
	* Scheduler computation periodically / Just In Time module
	* Multi-pos, multi-warehouse
	* Different reordering policies
	* Cost method by product: standard price, average price
	* Easy analysis of troubles or needs
	* Very flexible

	It support complete integration and plannification of stockable goods,
	consumable of services. Services are completly integrated with the rest
	of the software. For instance, you can set up a sub-contracting service
	in a BoM to automatically purchase on order the assembly of your production.

	Reports provided by this module:
	* Bill of Material structure and components
	* Load forecast on workcenters
	* Print a production order
	* Stock forecasts
	""",
	"init_xml" : [],
	"demo_xml" : ["mrp_demo.xml","mrp_order_point.xml"],
	"update_xml" : ["mrp_workflow.xml", "mrp_data.xml","mrp_view.xml", "mrp_wizard.xml", "mrp_report.xml"],
	"active": False,
	"installable": True
}
