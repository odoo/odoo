{
	"name" : "Module publisher",
	"version" : "1.0",
	"author" : "Tiny",
	"website" : "http://tinyerp.com",
	"category" : "Generic Modules/Base",
	"description": """
	This module can be used by developpers to automatically publish their modules
	in a few click to the following websites:
	* http://TinyERP.com, section module
	* http://TinyForge.org
	* PyPi, The python offical repository
	* http://Freshmeat.net

	It adds a button "Publish module" on each module, so that you simply have
	to call this button when you want to release a new version of your module.
	""",
	"depends" : ["base"],
	"init_xml" : [ ],
	"demo_xml" : [ ],
	"update_xml" : [ "base_module_publish_wizard.xml" ],
	"active": True,
	"installable": True
}
