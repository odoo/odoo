#
# Use the custom module to put your specific code in a separate module.
#
{
	"name" : "Add an automatic sequence on partners",
	"version" : "1.0",
	"author" : "Tiny",
	"category" : "Generic Modules/Base",
	"website": "http://www.tinyerp.com",
	"depends" : ["base"],
	"description": """
		This module adds the possibility to define a sequence for
		the partner code. This code is then set as default when you
		create a new partner, using the defined sequence.
	""",
	"demo_xml" : [],
	"init_xml" : ['partner_sequence.xml'],
	"update_xml" : [],
	"active": False,
	"installable": True
}
