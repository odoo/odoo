# Copyright (C) 2017 - Today: GRAP (http://www.grap.coop)
# @author: Sylvain LE GAL (https://twitter.com/legalsylvain)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "PoS Order To Sale Order",
    "version": "16.0.1.0.8",
    "author": "GRAP,Odoo Community Association (OCA)",
    "category": "Point Of Sale",
    "license": "AGPL-3",
    "depends": ["point_of_sale", "sale"],
    "maintainers": ["legalsylvain"],
    "development_status": "Production/Stable",
    "website": "https://github.com/OCA/pos",
    "data": ["views/view_res_config_settings.xml"],
    "assets": {
        "point_of_sale.assets": [
            "pos_order_to_sale_order/static/src/css/pos.css",
            "pos_order_to_sale_order/static/src/js/CreateOrderButton.js",
            "pos_order_to_sale_order/static/src/js/CreateOrderPopup.js",
            "pos_order_to_sale_order/static/src/xml/CreateOrderButton.xml",
            "pos_order_to_sale_order/static/src/xml/CreateOrderPopup.xml",
        ],
        "web.assets_tests": [
            "pos_order_to_sale_order/static/tests/**/*.js",
        ],
    },
    "installable": True,
}
