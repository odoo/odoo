{
	"name" : "Human Resources Expenses Tracking",
	"version" : "0.1",
	"author" : "Tiny",
	"category" : "Generic Modules/Human Resources",
	"website" : "http://tinyerp.com/module_hr.html",
	"depends" : ["hr","account", "account_tax_include",],
	"description": """
	This module aims to manage employee's expenses.

	The whole workflow is implemented:
	* Draft expense
	* Confirmation of the sheet by the employee
	* Validation by his manager
	* Validation by the accountant and invoice creation
	* Payment of the invoice to the employee

	This module also use the analytic accounting and is compatible with
	the invoice on timesheet module so that you will be able to automatcally
	re-invoice your customer's expenses if your work by project.
	""",
	"init_xml" : [],
	"demo_xml" : ["hr_expense_demo.xml", "hr.expense.expense.csv"],
	"update_xml" : ["hr_expense_sequence.xml", "hr_expense_workflow.xml", "hr_expense_view.xml", "hr_expense_report.xml",],
	"active": False,
	"installable": True
}
