{
	"name" : "Asset management",
	"version" : "1.0",
	"depends" : ["account", "account_simulation"],
	"author" : "Tiny",
	"description": """Financial and accounting asset management.""",
	"website" : "http://tinyerp.com/module_account.html",
	"category" : "Generic Modules/Accounting",
	"init_xml" : [
	],
	"demo_xml" : [
	],
	"update_xml" : [
		"account_asset_wizard.xml",
		"account_asset_view.xml",
		"account_asset_invoice_view.xml"
	],
#	"translations" : {
#		"fr": "i18n/french_fr.csv"
#	},
	"active": False,
	"installable": True
}
