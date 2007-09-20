{
	"name" : "report_account_analytic",
	"description": """Modifiy the account analytic view to show
important data for project manager of services companies.
Add menu to show relevant information for each manager.""",
	"version" : "1.0",
	"author" : "Camptocamp",
	"category" : "Generic Modules/Accounting",
	"module": "",
	"website": "http://www.camptocamp.com/",
	"depends" : ["account","hr_timesheet","hr_timesheet_invoice"],
	"init_xml" : [],
	"update_xml" : [
		"account_analytic_analysis_view.xml",
		"account_analytic_analysis_menu.xml",
	],
	"demo_xml" : [],
	"active": False,
	"installable": True
}
