{
	"name" : "Human Resources (Timesheet encoding)",
	"version" : "0.1",
	"author" : "Tiny",
	"category" : "Generic Modules/Human Resources",
	"website" : "http://tinyerp.com/module_hr.html",
	"description": """
	This module implement a timesheet system. Each employee can encode and
	track their time spent on the different projects. A project is an
	analytic account and the time spent on a project generate costs on
	the analytic account.

	Lots of reporting on time and employee tracking are provided.
	
	It is completly integrated with the cost accounting module. It allows you
	to set up a management by affair.
	""",
	"depends" : ["account", "hr", "base",],
	"init_xml" : ["hr_timesheet_data.xml"],
	"demo_xml" : ["hr_timesheet_demo.xml",],
	"update_xml" : ["hr_timesheet_view.xml", "hr_timesheet_report.xml","hr_timesheet_wizard.xml"],
	"active": False,
	"installable": True
}
