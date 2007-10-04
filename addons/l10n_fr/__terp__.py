#
# Plan comptable général pour la France, conforme au 
# Règlement n° 99-03 du 29 avril 1999
# Version applicable au 1er janvier 2005.
# Règlement disponible sur http://comptabilite.erp-libre.info
# Mise en forme et paramétrage par http://sisalp.fr et http://nbconseil.net
# 
{
	"name" : "France - Plan comptable Societe - 99-03",
	"version" : "1.1",
	"author" : "SISalp-NBconseil",
	"category" : "Localisation/Account charts",
	"website": "http://erp-libre.info",
	"depends" : ["base", "account", "account_chart", 'base_vat'],
	"init_xml" : [],
	"update_xml" : ["../account_chart/account_chart.xml", "types.xml",
		"plan-99-03_societe.xml", "taxes.xml",],
	"demo_xml" : [],
	"installable": True
}
