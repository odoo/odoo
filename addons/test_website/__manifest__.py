{
    "name": "Website Test",
    "version": "1.0",
    "category": "Hidden",
    "sequence": 9876,
    "summary": "Website Test, mainly for module install/uninstall tests",
    "description": """This module contains tests related to website. Those are
present in a separate module as we are testing module install/uninstall/upgrade
and we don't want to reload the website module every time, including it's possible
dependencies. Neither we want to add in website module some routes, views and
models which only purpose is to run tests.""",
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "web_unsplash",
        "website",
        "theme_default",
    ],
    "data": [
        "security/test_website_security.xml",
        "views/templates.xml",
        "views/test_model_multi_website_views.xml",
        "views/test_model_views.xml",
        "data/test_website_data.xml",
        "security/ir.access.csv",
        "views/test_website_menus.xml",
    ],
    "demo": [
        "demo/test_website_demo.xml",
    ],
    "assets": {
        "test_website.test_bundle": [
            "http://test.external.link/javascript1.js",
            "/web/static/src/libs/fontawesome7/css/fontawesome.css",
            "/web/static/src/libs/fontawesome7/css/solid.css",
            "/web/static/src/libs/fontawesome7/css/regular.css",
            "/web/static/src/libs/fontawesome7/css/brands.css",
            "http://test.external.link/style1.css",
            "http://test.external.link/javascript2.js",
            "http://test.external.link/style2.css",
        ],
        "web.assets_frontend": [
            "test_website/static/src/interactions/**/*",
        ],
        "web.assets_tests": [
            "test_website/static/tests/tours/*",
        ],
    },
}
