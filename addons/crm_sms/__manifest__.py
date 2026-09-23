{
    "name": "SMS in CRM",
    "version": "1.1",
    "category": "Sales/CRM",
    "summary": "Add SMS capabilities to CRM",
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "crm",
        "sms",
    ],
    "data": [
        "views/crm_lead_views.xml",
        "security/ir.access.csv",
    ],
    "auto_install": True,
}
