{
	"name" : "Human Resources (Timesheet groups)",
	"version" : "0.1",
	"author" : "Tiny",
	"category" : "Generic Modules/Human Resources",
	"website" : "http://tinyerp.com/module_hr.html",
	"description": "Timesheet by sheets",
	"depends" : ["hr_timesheet", "hr_timesheet_project", "hr_timesheet_invoice"],
	"init_xml" : [],
	"demo_xml" : [],
	"update_xml" : ["hr_timesheet_sheet_view.xml", "hr_timesheet_workflow.xml"],
	"active": False,
	"installable": True
}
