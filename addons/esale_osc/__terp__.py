{
	"name" : "OScommerce Interface / ZenCart",
	"version" : "1.0",
	"author" : "Tiny / modified by Lucien Moerkamp",
	"category" : "Interfaces/CMS & eCommerce",
	"website" : "http://www.tinyerp.com",
	"depends" : ["product", "stock", "sale"],
	"description": """OSCommerce (Zencart) eCommerce interface synchronisation.
Users can order on the website, orders are automatically imported in Tiny
ERP.

You can export products, stock level and create links between
categories of products, taxes and languages.

If you product has an image attched, it send the image to the Joomla website.""",
	"init_xml" : [],
	"demo_xml" : [],
	"update_xml" : ["esale_osc_view.xml", "esale_osc_wizard.xml"],
	"active": False,
	"installable": True
}
