# Copyright 2017 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Web Domain Field",
    "summary": """
        Use computed field as domain""",
    "version": "16.0.1.0.1",
    "license": "AGPL-3",
    "author": "ACSONE SA/NV,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/web",
    "depends": ["web"],
    "data": [],
    "assets": {
        "web.assets_backend": [
            "/web_domain_field/static/lib/js/*.js",
        ],
        "web.qunit_suite_tests": [
            "/web_domain_field/static/tests/**/*.js",
        ],
    },
    "installable": True,
}
