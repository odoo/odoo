#
# Use the custom module to put your specific code in a separate module.
# 
{
	"name" : "Module for custom developments",
	"version" : "1.0",
	"author" : "Tiny",
	"category" : "Generic Modules/Others",
	"website": "http://www.tinyerp.com",
	"description": "Sample custom module where you can put your customer specific developments.",
	"depends" : ["base"],
	"init_xml" : [],
	"update_xml" : ["custom_view.xml"],
	"active": False,
	"installable": True
}
