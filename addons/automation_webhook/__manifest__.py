{
    "name": "Automation Webhooks",
    "version": "1.0",
    "category": "Hidden",
    "summary": "The On webhook trigger for automation rules, behind the credential inbound gate",
    "author": "AgroMarin",
    "website": "https://www.agromarin.mx",
    "license": "LGPL-3",
    "depends": [
        "automation",
        "credential",
    ],
    "data": [
        "views/automation_rule_views.xml",
    ],
    "auto_install": [
        "automation",
    ],
    "pre_init_hook": "pre_init_hook",
}
