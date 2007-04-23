{
	"name" : "Network Management",
	"version" : "1.0",
	"author" : "Tiny",
	"category" : "Enterprise Specific Modules/Information Technology",
	"depends" : ["base"],
	"init_xml" : [],
	"description": """
	A simple module to encode your networks and materials:
	- networks and connections between networks
	- hardwares and softwares with:
		- versions, access rights, waranties

	You can print interventions form for technical people.""",
	"demo_xml" : ["network_demo.xml"],
	"update_xml" : ["network_view.xml", "network_report.xml"],
	"active" : False,
	"installable": True
}
