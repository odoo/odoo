{
	"name" : "Accounting and financial management",
	"version" : "1.0",
	"depends" : ["product", "base"],
	"author" : "Tiny",
	"description": """Financial and accounting module that covers:
	General accounting
	Cost / Analytic accounting
	Third party accounting
	Taxes management
	Budgets
	""",
	"website" : "http://tinyerp.com/module_account.html",
	"category" : "Generic Modules/Accounting",
	"init_xml" : [
	],
	"demo_xml" : [
		"account_demo.xml",
		"project/project_demo.xml",
		"project/analytic_account_demo.xml",
		"account_unit_test.xml",
	],
	"update_xml" : [
		"account_wizard.xml",
		"account_view.xml",
		"account_end_fy.xml",
		"account_invoice_view.xml",
		"account_report.xml",
		"partner_view.xml",
		"data/account_invoice.xml",
		"data/account_data1.xml",
		"data/account_minimal.xml",
		"data/account_data2.xml",
		"account_invoice_workflow.xml",
		"project/project_wizard.xml",
		"project/project_view.xml",
		"project/project_report.xml",
		"product_data.xml",
		"product_view.xml",
		
		"account_assert_test.xml",
		"account_security.xml",
		"project/project_security.xml",
	],
#	"translations" : {
#		"fr": "i18n/french_fr.csv"
#	},
	"active": False,
	"installable": True
}
