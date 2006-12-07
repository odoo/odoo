{
	"name" : "Base",
	"version" : "1.0",
	"author" : "Tiny",
	"website" : "http://tinyerp.com",
	"category" : "Generic Modules/Base",
	"description": "The kernel of Tiny ERP, needed for all installation.",
	"depends" : [],
	"init_xml" : [
		"base_data.xml",
		"base_menu.xml"
	],
	"demo_xml" : [
		"base_demo.xml",
		"res/partner/partner_demo.xml",
		"res/partner/crm_demo.xml",
	],
	"update_xml" : [
		"base_update.xml",
		"ir/ir.xml",
		"ir/workflow/workflow_view.xml",
		"module/module_data.xml",
		"module/module_wizard.xml",
		"module/module_view.xml",
		"module/module_report.xml",
		"res/res_request_view.xml",
		"res/partner/partner_report.xml",
		"res/partner/partner_view.xml",
		"res/partner/partner_wizard.xml",
		"res/res_currency_view.xml",
		"res/partner/crm_view.xml",
		"res/partner/partner_data.xml",
		"res/ir_property_view.xml",
	],
	"installable": True
}
