{
	"name":"Board for accountant",
	"version":"1.0",
	"author":"Tiny",
	"category":"Board/Accounting",
	"depends":[
		"account",
		"hr_timesheet_invoice",
		"board",
		"report_account",
		"report_analytic",
		"report_analytic_line",
		"account_report",
		"hr_timesheet_sheet"
	],
	"demo_xml":["board_account_demo.xml"],
	"update_xml":["board_account_view.xml"],
	"description": """
	This module creates a dashboards for accountants that includes:
	* List of analytic accounts to close
	* List of uninvoiced quotations
	* List of invoices to confirm
	* Graph of costs to invoice
	* Graph of aged receivables
	* Graph of aged incomes
	""",
	"active":False,
	"installable":True,
}
