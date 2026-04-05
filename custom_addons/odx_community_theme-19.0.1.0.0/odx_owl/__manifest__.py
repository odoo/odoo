# -*- coding: utf-8 -*-

{
    "name": "ODX UI Kit",
    "summary": "Reusable OWL components inspired by shadcn/ui",
    "description": """
A library of 60+ reusable OWL 2 components for Odoo 19 backend development,
inspired by shadcn/ui and Radix design patterns.

Includes: accordion, alert, badge, button, calendar, card, carousel, chart,
checkbox, combobox, data-table, date-picker, dialog, drawer, dropdown, form,
input, popover, select, slider, tabs, toast, tooltip, and more.
    """,
    "version": "19.0.1.0.0",
    "category": "Tools",
    "author": "Bashir Hassan",
    "website": "https://www.odxbuilder.com/",
    "support": "support@odxbuilder.com",
    "license": "LGPL-3",
    "images": ["static/description/Chat App Showcase.jpeg"],
    "depends": ["web"],
    "assets": {
        "odx_owl.assets_backend": [
            "odx_owl/static/src/scss/odx_owl.scss",
            "odx_owl/static/src/index.js",
            "odx_owl/static/src/core/utils/*.js",
            "odx_owl/static/src/components/*/*.js",
            "odx_owl/static/src/components/*/*.xml",
            "odx_owl/static/src/core/services/*.js",
        ],
        "web.assets_backend": [
            ("include", "odx_owl.assets_backend"),
        ],
        "web.assets_unit_tests": [
            "odx_owl/static/src/core/utils/*.js",
            "odx_owl/static/src/components/*/*.js",
            "odx_owl/static/src/components/*/*.xml",
            "odx_owl/static/src/core/services/*.js",
            "odx_owl/static/tests/**/*.js",
        ],
    },
    "application": False,
    "installable": True,
}
