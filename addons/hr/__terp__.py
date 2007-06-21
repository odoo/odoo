{
	"name" : "Human Resources",
	"version" : "0.1",
	"author" : "Tiny",
	"category" : "Generic Modules/Human Resources",
	"website" : "http://tinyerp.com/module_hr.html",
	"description": """
	Module for human resource management. You can manage:
	* Employees and hierarchies
	* Work hours sheets
	* Attendances and sign in/out system
	* Holidays

	Different reports are also provided, mainly for attendance statistics.
	""",
	"depends" : ["base"],
	"init_xml" : [],
	"demo_xml" : [
		"hr_demo.xml", 
		"hr_bel_holidays_2005.xml",
		"hr_department_demo.xml"
	],
	"update_xml" : [
		"hr_view.xml", 
		"hr_report.xml", 
		"hr_wizard.xml",
		"hr_department_view.xml"
	],
	"active": False,
	"installable": True
}
