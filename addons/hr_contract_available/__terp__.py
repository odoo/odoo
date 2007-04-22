{
	"name" : "Human Resources Contracts",
	"version" : "0.1",
	"author" : "Tiny",
	"category" : "Generic Modules/Human Resources",
	"website" : "http://tinyerp.com/module_hr.html",
	"depends" : ["hr_contract"],
	"module": "",
	"description": """
	This module is a reservation system on employees.

	You can assign an employee to a poste or a department for a
	defined period. This module is used to track availability and
	reservations on human ressources.
	""",
	"init_xml" : [],
	"demo_xml" : [],
	"update_xml" : ["hr_contract_available_view.xml"],
	"active": False,
	"installable": True
}
