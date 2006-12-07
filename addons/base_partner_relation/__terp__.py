{
	"name" : "Partners - relation extension",
	"version" : "1.0",
	"author" : "Tiny",
	"category" : "Generic Modules/CRM & SRM",
	"description" : """Add a tab in the partner form to encode relations between several partners.
	For eg, the partner 'Toubib and Co.' has different contacts.
	When 'Toubib and Co.' orders, you have to deliver to 'Toubib - Belgium'
	and invoice to 'Toubib - Geneva'.
	""",
	"depends" : ["base"],
	"init_xml" : [],
	"demo_xml" : [],
	"update_xml" : [
		"partner_relation_view.xml",
	],
	"active": False,
	"installable": True
}
