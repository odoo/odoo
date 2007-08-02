{
	"name" : "Timesheets",
	"version" : "1.0",
	"author" : "Tiny",
	"category" : "Generic Modules/Human Resources",
	"website" : "http://tinyerp.com/module_hr.html",
	"description": """
This module help you easily encode and validate timesheet and attendances
within the same view. The upper part of the view is for attendances and
track (sign in/sign out) events. The lower part is for timesheet.

Others tabs contains statistics views to help you analyse your
time or the time of your team:
* Time spent by day (with attendances)
* Time spent by project

This module also implement a complete timesheet validation process:
* Draft sheet
* Confirmation at the end of the period by the employee
* Validation by the project manager

The validation can be configured in te company:
* Period size (day, week, month, year)
* Maximal difference between timesheet and attendances
	""",
	"depends" : ["base", "hr_timesheet", "hr_timesheet_invoice"],
	"init_xml" : [],
	"demo_xml" : ["hr_timesheet_sheet_demo.xml",],
	"update_xml" : ["hr_timesheet_sheet_view.xml", "hr_timesheet_workflow.xml"],
	"active": False,
	"installable": True
}
