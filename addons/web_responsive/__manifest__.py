# Copyright 2016-2017 LasLabs Inc.
# Copyright 2017-2018 Tecnativa - Jairo Llopis
# Copyright 2018-2019 Tecnativa - Alexandre Díaz
# Copyright 2021 ITerra - Sergey Shebanin
# Copyright 2023 Onestein - Anjeel Haria
# Copyright 2023 Taras Shabaranskyi
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

{
    "name": "Web Responsive",
    "summary": "Responsive web client, community-supported",
    "version": "18.0.1.0.2",
    "category": "Website",
    "website": "https://github.com/OCA/web",
    "author": "LasLabs, Tecnativa, ITerra, Onestein, "
    "Odoo Community Association (OCA)",
    "license": "LGPL-3",
    "installable": True,
    "depends": ["web", "web_tour", "mail"],
    "development_status": "Production/Stable",
    "maintainers": ["Tardo", "SplashS"],
    "excludes": ["web_enterprise"],
    "data": [
        "views/res_users_views.xml",
    ],
    "assets": {
        "web._assets_primary_variables": {
            "/web_responsive/static/src/legacy/scss/form_variable.scss",
            "/web_responsive/static/src/legacy/scss/primary_variable.scss",
        },
        "web.assets_backend": [
            "web_responsive/static/src/lib/fuse/fuse.basic.min.js",
            "/web_responsive/static/src/legacy/scss/web_responsive.scss",
            "/web_responsive/static/src/legacy/scss/big_boxes.scss",
            "/web_responsive/static/src/legacy/scss/list_sticky_header.scss",
            "/web_responsive/static/src/legacy/js/web_responsive.esm.js",
            "/web_responsive/static/src/legacy/xml/form_buttons.xml",
            "/web_responsive/static/src/legacy/xml/custom_favorite_item.xml",
            "/web_responsive/static/src/components/apps_menu_tools.esm.js",
            "/web_responsive/static/src/components/apps_menu/*",
            "/web_responsive/static/src/components/apps_menu_item/*",
            "/web_responsive/static/src/components/menu_canonical_searchbar/*",
            "/web_responsive/static/src/components/menu_odoo_searchbar/*",
            "/web_responsive/static/src/components/menu_fuse_searchbar/*",
            "/web_responsive/static/src/components/menu_searchbar/*",
            "/web_responsive/static/src/components/hotkey/*",
            "/web_responsive/static/src/components/file_viewer/*",
            "/web_responsive/static/src/components/chatter/*",
            "/web_responsive/static/src/components/control_panel/*",
            "/web_responsive/static/src/components/command_palette/*",
            "/web_responsive/static/src/views/form/*",
        ],
        "web.assets_clickbot": [
            "/web_responsive/static/src/clickbot/clickbot.esm.js",
        ],
        "web.qunit_suite_tests": [
            "/web_responsive/static/tests/apps_menu_tests.esm.js",
            "/web_responsive/static/tests/apps_menu_search_tests.esm.js",
        ],
    },
    "sequence": 1,
}
