# Copyright 2016 ACSONE SA/NV (<http://acsone.eu>)
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).
{
    "name": "Date Range",
    "summary": "Manage all kind of date range",
    "version": "16.0.1.0.9",
    "category": "Uncategorized",
    "website": "https://github.com/OCA/server-ux",
    "author": "ACSONE SA/NV, Odoo Community Association (OCA)",
    "license": "LGPL-3",
    "installable": True,
    "depends": [
        "web",
    ],
    "data": [
        "data/ir_cron_data.xml",
        "security/ir.model.access.csv",
        "security/date_range_security.xml",
        "views/date_range_view.xml",
        "wizard/date_range_generator.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "date_range/static/src/js/date_range.esm.js",
            "date_range/static/src/xml/date_range.xml",
        ],
    },
    "development_status": "Mature",
    "maintainers": ["lmignon"],
}
