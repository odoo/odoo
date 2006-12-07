{
	"name" : "Base Setup",
	"version" : "1.0",
	"author" : "Tiny",
	"website" : "http://tinyerp.com",
	"category" : "Generic Modules/Base",
	"description": "This module adds a wizard when the user connects for the first time in the system. If you do not want this setup wizard at first connection, just desactivate this module.",
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
