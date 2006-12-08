#
# Use the custom module to put your specific code in a separate module.
# 
{
	"name" : "Switzerland localisation",
	"version" : "1.0",
	"author" : "Camptocamp",
	"category" : "Localisation/Europe",
	"website": "http://www.tinyerp.com",
	"depends" : ["base", "account"],
	"init_xml" : [],#"zip_code_default.xml"
	"demo_xml" : ["vaudtax_data_demo.xml"],
	#	"update_xml" : ["vaudtax_data.xml","account_vat.xml","base_config.xml","account_config.xml"],
	"update_xml" : ["dta/dta_view.xml","v11/v11_view.xml","v11/v11_wizard.xml"],
	"active": False,
	"installable": True,
}
