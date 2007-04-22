{
	"name" : "Accounting follow-ups management",
	"version" : "1.0",
	"depends" : ["account"],
	"author" : "Tiny",
	"description": """
	Modules to automate letters for unpaid invoices, with multi-level recalls.

	You can define your multiple levels of recall through the menu:
		Financial Management/Configuration/Payment Terms/Follow-Ups

	Once it's defined, you can automatically prints recall every days
	through simply clicking on the menu:
		Financial_Management/Periodical_Processing/Print_Follow-Ups

	It will generate a PDF with all the letters according the the
	different levels of recall defined. You can define different policies
	for different companies.""",
	"website" : "http://tinyerp.com/module_account.html",
	"category" : "Generic Modules/Accounting",
	"init_xml" : [],
	"demo_xml" : ["followup_demo.xml"],
	"update_xml" : ["followup_view.xml"],
	"active": False,
	"installable": True
}

