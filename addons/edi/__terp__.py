{
	"name" : "EDI",
	"version" : "1.0",
	"author" : "Tiny",
	"depends" : ["sale"],
	"category" : "Interfaces/EDI",
	'description': "Used for the communication with others proprietary ERP's. Has been tested in the food industries process, communicating with SAP. This module is able to import order and export delivery notes.",
	"init_xml" : [],
	"demo_xml" : [],
	"update_xml" : ["edi_wizard.xml", "edi_view.xml", "edi_data.xml", "sale_cust_price.xml"],
	"active": False,
	"installable": True
}
