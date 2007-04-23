{
	"name" : "Base Setup",
	"version" : "1.0",
	"author" : "Tiny",
	"website" : "http://tinyerp.com",
	"category" : "Generic Modules/Base",
	"description": """
	This module implements a configuration system that helps user
	to configure the system at the installation of a new database.

	It allows you to select between a list of profiles to install:
	* Minimal profile
	* Accounting only
	* Services companies
	* Manufacturing companies

	It also asks screens to help easily configure your company, the header and
	footer, the account chart to install and the language.
	""",
	"depends" : ["base"],
	"init_xml" : [
		"base_setup_data.xml",
	],
	"demo_xml" : [
		"base_setup_demo.xml",
	],
	"update_xml" : [
		"base_setup_wizard.xml",
	],
	"active": True,
	"installable": True
}
