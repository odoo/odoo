# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    "name": "Translation Server",
    "category": "Tools",
    "summary": "Offer a translations server with languages packs",
    "description": """
This module provides standard routes to serve translations for downloadable language packs.
""",
    "depends": ["http_routing"],
    "data": [
        "security/ir.model.access.csv",
        "data/cron.xml",
        "views/i18n_views.xml",
        "views/server_templates.xml",
    ],
}
