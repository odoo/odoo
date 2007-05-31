{
	"name" : "eSale Interface - Joomla",
	"version" : "1.0",
	"author" : "Tiny",
	"category" : "Interfaces/CMS & eCommerce",
	"website" : "http://tinyerp.com",
	"depends" : ["product", "stock", "sale", "account", "account_tax_include",],
	"description": """Joomla (Virtuemart) eCommerce interface synchronisation.
Users can order on the website, orders are automatically imported in Tiny
ERP.

You can export products, stock level and create links between
categories of products, taxes and languages.

If you product has an image attched, it send the image to the Joomla website.""",
	"init_xml" : [],
	"demo_xml" : [],
	"update_xml" : ['esale_joomla_wizard.xml', "esale_joomla_view.xml"],
	"active": False,
	"installable": True
}
