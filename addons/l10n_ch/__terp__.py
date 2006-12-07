#
# Use the custom module to put your specific code in a separate module.
# 
{
	"name" : "Switzerland localisation",
	"version" : "1.0",
	"author" : "Camptocamp",
	"category" : "Localisation/Europe",
	"website": "http://www.tinyerp.com",
	"depends" : ["base", "account"],#l10n_ch
	"init_xml" : [],
	"demo_xml" : [],#"zip_code_default.xml"
	"update_xml" : ["vaudtax_data.xml","account_vat.xml","base_config.xml","account_config.xml"],
	#"update_xml" : ["vaudtax_data.xml"],
	"active": False,
	"installable": True
}
