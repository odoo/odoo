{
    "name": "Automation Webhooks",
    "version": "1.2",
    "category": "Hidden",
    "summary": "The On webhook trigger for automation rules, behind the credential inbound gate",
    "author": "AgroMarin",
    "website": "https://www.agromarin.mx",
    "license": "LGPL-3",
    "depends": [
        "integration",
        "automation",
    ],
    "data": [
        "views/automation_rule_views.xml",
    ],
    "auto_install": True,
    "pre_init_hook": "pre_init_hook",
}
