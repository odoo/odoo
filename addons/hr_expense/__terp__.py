{
	"name" : "Human Resources Expenses Tracking",
	"version" : "0.1",
	"author" : "Tiny",
	"category" : "Generic Modules/Human Resources",
	"website" : "http://tinyerp.com/module_hr.html",
	"depends" : ["hr","account", "account_tax_include",],
	"module": "This module manage the whole expenses flow. It also uses the cost accounting to put costs on analytic accounts.",
	"init_xml" : [],
	"demo_xml" : [],
	#"demo_xml" : ["hr_expense_demo.xml", "hr.expense.expense.csv"],
	"update_xml" : ["hr_expense_workflow.xml", "hr_expense_view.xml", "hr_expense_report.xml"],
	"active": False,
	"installable": True
}
