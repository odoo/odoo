{
    "name": "Partner Autocomplete",
    "version": "1.2",
    "category": "Hidden/Tools",
    "summary": "Auto-complete partner companies' data",
    "description": """
Auto-complete partner companies' data
    """,
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "iap_mail",
    ],
    "external_dependencies": {
        "python": [
            "python-stdnum",
        ],
        "apt": {
            "python-stdnum": "python3-stdnum",
        },
    },
    "data": [
        "security/ir.access.csv",
        "views/res_company_views.xml",
        "views/res_config_settings_views.xml",
        "data/iap_service_data.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "partner_autocomplete/static/src/scss/*",
            "partner_autocomplete/static/src/js/*",
            "partner_autocomplete/static/src/xml/*",
        ],
        "web.jsvat_lib": [
            "partner_autocomplete/static/lib/**/*",
        ],
        "web.assets_unit_tests": [
            "partner_autocomplete/static/tests/**/*",
        ],
    },
}
