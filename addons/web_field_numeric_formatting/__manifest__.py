# Copyright 2023 Odoo S.A.
# License LGPL-3.0 (https://www.gnu.org/licenses/lgpl-3.0)
{
    "name": "Web Numeric Field Formatting",
    "summary": "Allow to render float and integer fields without thousands separator",
    "category": "web",
    "version": "16.0.1.0.0",
    "author": "Opener B.V., Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/web",
    "depends": ["web"],
    "assets": {
        "web.assets_backend": [
            "web_field_numeric_formatting/static/src/components/float_field.esm.js",
            "web_field_numeric_formatting/static/src/components/integer_field.esm.js",
            "web_field_numeric_formatting/static/src/components/list_renderer.esm.js",
        ],
        "web.qunit_suite_tests": [
            "web_field_numeric_formatting/static/tests/field_tests.esm.js",
        ],
    },
    "license": "LGPL-3",
    "auto_install": False,
    "installable": True,
}
