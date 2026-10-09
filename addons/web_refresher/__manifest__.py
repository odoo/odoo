{
    "name": "Web Refresher",
    "version": "16.0.3.1.3",
    "author": "Compassion Switzerland, Tecnativa, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "website": "https://github.com/OCA/web",
    "depends": ["web"],
    "installable": True,
    "auto_install": False,
    "assets": {
        "web.assets_backend": [
            "web_refresher/static/src/**/*.scss",
            "web_refresher/static/src/xml/refresher.xml",
            # Load the modification of the master template just after it,
            # for having the modification in all the primary extensions.
            # Example: the project primary view.
            (
                "after",
                "web/static/src/search/control_panel/control_panel.js",
                "web_refresher/static/src/**/*.esm.js",
            ),
            (
                "after",
                "web/static/src/search/control_panel/control_panel.xml",
                "web_refresher/static/src/xml/control_panel.xml",
            ),
            (
                "after",
                "web/static/src/views/form/control_panel/form_control_panel.xml",
                "web_refresher/static/src/xml/form_control_panel.xml",
            ),
        ],
    },
}
