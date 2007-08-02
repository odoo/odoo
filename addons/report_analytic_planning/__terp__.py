{
	"name" : "Analytic planning - Reporting",
	"version" : "1.0",
	"author" : "Tiny",
	"website" : "http://tinyerp.com",
	"depends" : ["account", "hr_timesheet_invoice","project","report_analytic_line"],
	"category" : "Generic Modules/Accounting",
	"description": "Planning on analytic accounts.",
	"init_xml" : [],
	"demo_xml" : [
		"report_account_analytic.planning.csv"
	],
	"update_xml" : [
		"report_analytic_planning_view.xml",
		"report_analytic_planning_report.xml"
	],
	"active": False,
	"installable": True
}
