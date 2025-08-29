# Copyright (C) 2020 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Base Territory",
    "summary": "This module allows you to define territories, branches,"
    " districts and regions to be used for Field Service operations or Sales.",
    "version": "18.0.1.0.0",
    "category": "Hidden",
    "author": "Open Source Integrators, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/field-service",
    "depends": ["base"],
    "data": [
        "security/ir.model.access.csv",
        "views/res_territory.xml",
        "views/res_branch.xml",
        "views/res_district.xml",
        "views/res_region.xml",
        "views/res_country.xml",
        "views/menu.xml",
    ],
    "demo": ["demo/base_territory_demo.xml"],
    "application": True,
    "license": "AGPL-3",
    "development_status": "Production/Stable",
    "maintainers": ["max3903", "brian10048"],
}
