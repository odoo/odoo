#
# Use the custom module to put your specific code in a separate module.
# 
{
	"name" : "Switzerland localisation",
	"version" : "1.0",
	"author" : "Camptocamp",
	"category" : "Localisation/Europe",
	"website": "http://www.tinyerp.com",
	"depends" : ["base", "account", "account_cash_discount", "l10n_euro"],
	"init_xml" : ["dta/dta_data.xml", "vaudtax_data.xml"], #, "zip_code_default.xml",],
	"demo_xml" : ["vaudtax_data_demo.xml","dta/dta_demo.xml"],
	"update_xml" : [
		"dta/dta_view.xml","dta/dta_wizard.xml",
		"v11/v11_wizard.xml","v11/v11_view.xml",
		"account_vat.xml","base_config.xml","account_config.xml",
		"bvr/bvr_report.xml",
		"bvr/bvr_wizard.xml",
		"company_view.xml",
		#"partner_view.xml",
	],
	"active": False,
	"installable": True,
}
