{
    "name": "RPC endpoints",
    "version": "1.1",
    "category": "Hidden/Tools",
    "description": """Standard Odoo RPC endpoints to models
=====================================

This module provides the /xmlrpc/2 and /json/2 endpoints used to
programmatically access models, and the contract documents a client reads
before it calls them: /doc/index.json and /doc/<model>.json, under a session
or a bearer key. machine_doc_v1/openapi.json is the doors' own OpenAPI
description; api_doc renders all of it as a playground.
""",
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "base",
    ],
    "data": [
        "security/res_groups.xml",
    ],
    "auto_install": True,
}
