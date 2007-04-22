{
	"name" : "Analytic accounts with multiple partners",
	"author" : "Tiny",
	"version" : "1.0",
	"category" : "Generic Modules/Others",
	"depends" : ["account"],
	"description": """
	This module adds the possibility to assign multiple partners on
	the same analytic account. It's usefull when you do a management
	by affairs, where you can attach all suppliers and customers to
	a project.

	A report for the project manager is added to print the analytic
	account and all associated partners with their contacts.

	It's usefull to give to all members of a project, so that they
	get the contacts of all suppliers in this project.
	"""
	"demo_xml" : [],
	"update_xml" : ["analytic_partners_view.xml",
                        "analytic_partners_report.xml"],
	"init_xml" : [],
	"active": False,
	"installable": True
}
