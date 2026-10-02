# Copyright 2009 NetAndCo (<http://www.netandco.net>).
# Copyright 2011 Akretion Benoît Guillot <benoit.guillot@akretion.com>
# Copyright 2014 prisnet.ch Seraphine Lantible <s.lantible@gmail.com>
# Copyright 2016 Serpent Consulting Services Pvt. Ltd.
# Copyright 2018 Daniel Campos <danielcampos@avanzosc.es>
# Copyright 2018 Tecnativa - David Vidal
# Copyright 2019 Giovanni - GSLabIt
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Product Brand Manager",
    "version": "16.0.1.0.2",
    "development_status": "Mature",
    "category": "Product",
    "summary": "Product Brand Manager",
    "author": "NetAndCo, Akretion, Prisnet Telecommunications SA, "
    "MONK Software, SerpentCS Pvt. Ltd., Tecnativa, Kaushal "
    "Prajapati, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/brand",
    "license": "AGPL-3",
    "depends": ["sale"],
    "data": [
        "security/ir.model.access.csv",
        "views/product_brand_view.xml",
        "reports/sale_report_view.xml",
        "reports/account_invoice_report_view.xml",
    ],
    "installable": True,
    "auto_install": False,
}
