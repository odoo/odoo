{
	"name" : "Belgium - Plan Comptable Minimum Normalise",
	"version" : "1.1",
	"author" : "Tiny",
	"category" : "Localisation/Account charts",
	"depends" : ["account", "account_report", "base_vat", "base_iban",
		"account_chart"],
	"init_xml" : [],
	"demo_xml" : ["account_demo.xml","account.report.report.csv"],
	"update_xml" : ["../account_chart/account_chart.xml", "account_pcmn_belgium.xml"],
	"installable": True
}
