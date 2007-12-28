{
	"name": "Payment Management",
	"version": "1.0",
	"author": "Tiny",
	"category": "Generic Modules/Payment",
	"depends": ["account"],
	"init_xml": [],
	"description": """
	This module provide :
	* a more efficient way to manage invoice payment.
	* a basic mechanism to easily plug various automated payment.
	""",
	"demo_xml": [],
	"update_xml": ["payment_wizard.xml", "payment_view.xml",
		"payment_workflow.xml", "payment_sequence.xml",
		"account_invoice_view.xml", "payment_report.xml"],
	"active": False,
	"installable": True
}

