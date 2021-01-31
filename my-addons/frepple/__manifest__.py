# -*- coding: utf-8 -*-
{
    "name": "frepple",
    "version": "6.5.0",
    "category": "Manufacturing",
    "summary": "Advanced planning and scheduling",
    "author": "frePPLe",
    "website": "https://frepple.com",
    "license": "AGPL-3",
    "description": "Connector to frePPLe - finite capacity planning and scheduling",
    "depends": ["product", "purchase", "sale", "resource", "mrp"],
    "external_dependencies": {"python": ["jwt"]},
    "data": [
        "views/frepple_data.xml",
        "views/res_config_settings_views.xml",
        "security/frepple_security.xml",
    ],
    "demo": ["data/demo.xml"],
    "test": [],
    "installable": True,
    "auto_install": True,
}
