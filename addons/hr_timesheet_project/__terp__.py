{
	"name" : "Human Resources (Timesheet encoding from project tasks)",
	"version" : "1.0",
	"author" : "Tiny",
	"category" : "Generic Modules/Human Resources",
	"description": """Auto-complete timesheet based on tasks made on the project management module.""",
	"website" : "http://tinyerp.com/module_hr.html",
	"depends" : ["project", "hr_timesheet"],
	"update_xml" : ["hr_timesheet_project_view.xml"],
	"active": False,
	"installable": True
}
