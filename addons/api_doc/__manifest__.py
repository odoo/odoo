{
    "name": "API Documentation",
    "version": "1.0",
    "category": "Hidden",
    "description": """
Odoo Dynamic API Documentation
==============================

This module renders the contract documents `rpc` serves -- /doc/index.json
and /doc/<model>.json, the registry's models, fields and methods -- as a
single page at /doc, with a playground that runs a method over HTTP and
shows the call in several languages.

The documents themselves, the group that may read them and their cache are
`rpc`'s: a client that reads the contract needs no page, and a database with
no web client still serves it.
""",
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "rpc",
        "web",
    ],
    "data": [
        "views/docclient.xml",
    ],
    "assets": {
        "api_doc.assets": [
            "web/static/src/libs/fontawesome7/css/fontawesome.css",
            "web/static/src/libs/fontawesome7/css/solid.css",
            "web/static/src/libs/fontawesome7/css/regular.css",
            "web/static/src/libs/fontawesome7/css/brands.css",
            "web/static/src/scss/rtl_icon_flip.scss",
            "web/static/src/core/utils/functions.js",
            "web/static/src/core/utils/reactive.js",
            "web/static/src/core/browser/browser.js",
            "web/static/src/core/utils/timing.js",
            "web/static/src/core/template_inheritance.js",
            "web/static/src/core/templates.js",
            "web/static/src/core/registry.js",
            "web/static/src/session.js",
            "web/static/src/core/module_bridge.js",
            "web/static/src/core/utils/asset_log.js",
            "web/static/src/core/utils/global_singleton.js",
            "web/static/src/core/utils/bundle_transaction.js",
            "web/static/src/core/assets.js",
            "web/static/src/components/code_editor/**",
            (
                "include",
                "web._assets_helpers",
            ),
            "web/static/src/scss/pre_variables.scss",
            "web/static/lib/bootstrap/scss/_variables.scss",
            "web/static/lib/bootstrap/scss/_variables-dark.scss",
            "web/static/lib/bootstrap/scss/_maps.scss",
            (
                "include",
                "web._assets_bootstrap",
            ),
            "api_doc/static/src/**/*.xml",
            "api_doc/static/src/**/*.js",
            "api_doc/static/src/doc_client.css",
            (
                "remove",
                "api_doc/static/src/api_action.js",
            ),
        ],
        "web.assets_backend": [
            "api_doc/static/src/api_action.js",
        ],
        "web.assets_unit_tests": [
            "api_doc/static/src/utils/doc_model_search.js",
            "api_doc/static/src/utils/doc_model_utils.js",
            "api_doc/static/tests/**/*.test.js",
        ],
    },
    "esm": {
        "bundles": [
            "api_doc.assets",
        ],
    },
    "bootstrap": True,
    "auto_install": True,
}
