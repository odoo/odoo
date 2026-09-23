{
    "name": "Mail Plugin",
    "version": "1.0",
    "category": "Sales/CRM",
    "sequence": 5,
    "summary": "Allows integration with mail plugins.",
    "description": "Integrate Odoo with your mailbox, get information about contacts directly inside your mailbox, log content of emails as internal notes",
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "web",
        "partner",
        "iap",
    ],
    "data": [
        "data/res_users_apikeys_scope_data.xml",
        "views/mail_plugin_login.xml",
        "views/res_partner_iap_views.xml",
        "security/ir.access.csv",
        "views/mail_plugin_menus.xml",
    ],
}
