# © 2010-2013 OpenERP s.a. (<http://openerp.com>).
# © 2014 initOS GmbH & Co. KG (<http://www.initos.com>).
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html
{
    "name": "Overview Dashboard (Tiles)",
    "summary": "Add Overview Dashboards with Tiles",
    "version": "19.0.1.0.0",
    "application": True,
    "installable": True,
    "depends": [
        "web",
        "spreadsheet_dashboard",
    ],
    "author": "initOS GmbH & Co. KG, "
    "GRAP, "
    "Iván Todorovich <ivan.todorovich@gmail.com>, "
    "Odoo Community Association (OCA)",
    "maintainers": ["legalsylvain"],
    "website": "https://github.com/OCA/web",
    "category": "web",
    "license": "AGPL-3",
    "data": [
        "security/ir.model.access.csv",
        "security/ir_rule.xml",
        "views/menu.xml",
        "views/tile_tile.xml",
        "views/tile_category.xml",
    ],
    "assets": {
        "web.assets_common": [
            "web_dashboard_tile/static/src/css/web_dashboard_tile.css",
        ],
    },
    "demo": [
        "demo/tile_category.xml",
        "demo/tile_tile.xml",
    ],
    "post_init_hook": "_post_init_hook",
}
