{
	"name" : "Customer & Supplier Relationship Management",
	"version" : "1.0",
	"author" : "Tiny",
	"website" : "http://tinyerp.com/module_crm.html",
	"category" : "Generic Modules/CRM & SRM",
	"description": """The Tiny ERP case and request tracker enables a group of
people to intelligently and efficiently manage tasks, issues, and requests.
It manages key tasks such as communication, identification, prioritization,
assignment, resolution and notification.

Tiny ERP ensures that all cases are successfly tracked by users, customers and
suppliers. It can automatically send reminders, escalate the request, trigger
specific methods and lots of others actions based on your enterprise own rules.

The greatest thing about this system is that users don't need to do anything
special. They can just send email to the request tracker. Tiny ERP will take
care of thanking them for their message, automatically routing it to the
appropriate staff, and making sure all future correspondence gets to the right
place.

The CRM module has a email gateway for the synchronisation interface
between mails and Tiny ERP.""",
	"depends" : ["base"],
	"init_xml" : ["crm_data.xml"],
	"demo_xml" : ["crm_demo.xml"],
	"update_xml" : ["crm_view.xml", "crm_report.xml", "crm_wizard.xml", "crm_security.xml"],
	"active": False,
	"installable": True
}
