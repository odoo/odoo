# Copyright 2020 Tecnativa - Manuel Calero
# Copyright 2022 Quartile
# Copyright 2014-2022 Tecnativa - Pedro M. Baeza
{
    "name": "Sales commissions",
    "version": "16.0.1.0.2",
    "author": "Tecnativa, Odoo Community Association (OCA)",
    "category": "Sales Management",
    "license": "AGPL-3",
    "depends": [
        "sale",
        "account_commission",
    ],
    "website": "https://github.com/OCA/commission",
    "maintainers": ["pedrobaeza"],
    "data": [
        "security/ir.model.access.csv",
        "views/sale_order_view.xml",
    ],
    "installable": True,
}
