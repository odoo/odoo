{
	"name" : "Manufacturing Resource Planning",
	"version" : "1.0",
	"author" : "Tiny",
	"website" : "http://tinyerp.com/module_mrp.html",
	"category" : "Generic Modules/Production",
	"depends" : ["stock", "hr", "purchase", "product"],
	"description": "Manage the manufacturing process: procurement, scheduler computation, bill of materials, routings, procurements, production orders, workcenters, eso.",
	"init_xml" : [],
	"demo_xml" : ["mrp_demo.xml","mrp_order_point.xml"],
	"update_xml" : ["mrp_workflow.xml", "mrp_data.xml","mrp_view.xml", "mrp_wizard.xml", "mrp_report.xml"],
	"active": False,
	"installable": True
}
