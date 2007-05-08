{
	"name" : "Invoice on timesheet",
	"version" : "1.0",
	"author" : "Tiny",
	"category" : "Generic Modules/Human Resources",
	"website" : "http://tinyerp.com/module_hr.html",
	"depends" : ["account",'hr_timesheet'],
	"description": """
Module to generate invoices based on costs (human ressources, expenses, ...).
You can define pricelists in analytic account, make some theorical revenue
reports, eso.""",
	"init_xml" : [],
	"demo_xml" : [
		'hr_timesheet_invoice_demo.xml'
	],
	"update_xml" : [
		'hr_timesheet_invoice_view.xml',
		'hr_timesheet_invoice_wizard.xml',
		'hr_timesheet_invoice_report.xml'
	],
	"active": False,
	"installable": True
}
