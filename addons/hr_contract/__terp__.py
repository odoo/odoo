{
	"name" : "Human Resources Contracts",
	"version" : "1.0",
	"author" : "Tiny",
	"category" : "Generic Modules/Human Resources",
	"website" : "http://tinyerp.com/module_hr.html",
	"depends" : ["hr"],
	"module": "",
	"description": """
	Add all information on the employee form to manage contracts:
	* Martial status,
	* Security number,
	* Place of birth, birth date, ...

	You can assign several contracts per employee.
	""",
	"init_xml" : ["hr_contract_data.xml", "hr_contract_security.xml"],
	"demo_xml" : [],
	"update_xml" : [
		"hr_contract_view.xml",
		
	],
	"active": False,
	"installable": True
}
