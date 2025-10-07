# Copyright (C) 2014-Today GRAP (http://www.grap.coop)
# Copyright (C) 2016-Today La Louve (http://www.lalouve.net)
# Copyright (C) 2018 Komit (https://komit-consulting.com)
# @author: Sylvain LE GAL (https://twitter.com/legalsylvain)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "Generate Barcodes (Abstract)",
    "summary": "Generate Barcodes for Any Models",
    "version": "16.0.3.0.6",
    "category": "Tools",
    "author": "GRAP, La Louve, LasLabs, Odoo Community Association (OCA)",
    "maintainers": ["legalsylvain"],
    "website": "https://github.com/OCA/stock-logistics-barcode",
    "license": "AGPL-3",
    "depends": ["barcodes"],
    "data": [
        "security/res_groups.xml",
        "views/view_barcode_rule.xml",
        "views/view_barcode_nomenclature.xml",
        "views/menu.xml",
    ],
    "demo": ["demo/res_users.xml"],
    "external_dependencies": {"python": ["python-barcode"]},
}
