{
    "name": "Lead Generation From Website Visits",
    "version": "1.1",
    "category": "Sales/CRM",
    "summary": "Generate Leads/Opportunities from your website's traffic",
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "iap_crm",
        "iap_mail",
        "crm_iap_mine",
        "website_crm",
    ],
    "data": [
        "data/ir_cron_data.xml",
        "data/ir_model_data.xml",
        "security/ir.access.csv",
        "views/crm_lead_views.xml",
        "views/crm_reveal_views.xml",
        "views/res_config_settings_views.xml",
        "views/crm_menus.xml",
    ],
}
