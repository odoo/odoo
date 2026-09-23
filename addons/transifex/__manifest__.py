{
    "name": "Transifex integration",
    "version": "1.0",
    "category": "Hidden/Tools",
    "summary": "Add a link to edit a translation in Transifex",
    "description": """
Transifex integration
=====================
This module will add a link to the Transifex project in the translation view.
The purpose of this module is to speed up translations of the main modules.

To work, Odoo uses Transifex configuration files `.tx/config` to detect the
project source. Custom modules will not be translated (as not published on
the main Transifex project).

The language the user tries to translate must be activated on the Transifex
project.
        """,
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "base",
        "web",
    ],
    "data": [
        "data/transifex_data.xml",
        "views/code_translation_views.xml",
        "security/ir.access.csv",
        "views/transifex_menus.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "transifex/static/src/views/fields/translation_dialog.xml",
            "transifex/static/src/views/*.js",
            "transifex/static/src/views/*.xml",
        ],
    },
}
