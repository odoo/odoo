{
	"name" : "Sale CRM Stuff",
	"version" : "1.0",
	"author" : "Tiny",
	"website" : "http://tinyerp.com/module_sale.html",
	"depends" : ["sale", "crm"],
	"category" : "Generic Modules/Sales & Purchases",
	"description": """
	This module adds a shortcut on one or several cases in the CRM.
	This shortcut allows you to generate a sale order based the selected case.
	If different cases are open (a list), it generates one sale order by
	case.

	The case is then closed and linked to the generated sale order.
	""",
	"init_xml" : [],
	"demo_xml" : [],
	"update_xml" : ["sale_crm_wizard.xml"],
	"active": False,
	"installable": True
}
