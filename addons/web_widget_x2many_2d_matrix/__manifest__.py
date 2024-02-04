# Copyright 2015 Holger Brunn <hbrunn@therp.nl>
# Copyright 2016 Pedro M. Baeza <pedro.baeza@tecnativa.com>
# Copyright 2018 Simone Orsi <simone.orsi@camptocamp.com>
# Copyright 2020 CorporateHub (https://corporatehub.eu)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    "name": "2D matrix for x2many fields",
    "version": "16.0.1.1.2",
    "maintainers": ["ChrisOForgeFlow"],
    "development_status": "Production/Stable",
    "author": (
        "Therp BV, "
        "Tecnativa, "
        "Camptocamp, "
        "CorporateHub, "
        "Onestein, "
        "Odoo Community Association (OCA)"
    ),
    "website": "https://github.com/OCA/web",
    "license": "AGPL-3",
    "category": "Hidden/Dependency",
    "summary": "Show list fields as a matrix",
    "depends": ["web"],
    "data": [],
    "installable": True,
    "assets": {
        "web.assets_backend": [
            "web_widget_x2many_2d_matrix/static/src/components/x2many_2d_matrix_renderer/"
            "x2many_2d_matrix_renderer.esm.js",
            "web_widget_x2many_2d_matrix/static/src/components/x2many_2d_matrix_renderer/"
            "x2many_2d_matrix_renderer.xml",
            "web_widget_x2many_2d_matrix/static/src/components/x2many_2d_matrix_field/"
            "x2many_2d_matrix_field.esm.js",
            "web_widget_x2many_2d_matrix/static/src/components/x2many_2d_matrix_field/"
            "x2many_2d_matrix_field.xml",
            "web_widget_x2many_2d_matrix/static/src/components/x2many_2d_matrix_field/"
            "x2many_2d_matrix_field.scss",
        ],
    },
}
