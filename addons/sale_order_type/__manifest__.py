# Copyright 2015 Carlos Sánchez Cifuentes <csanchez@grupovermon.com>
# Copyright 2015-2016 Oihane Crucelaegui <oihane@avanzosc.com>
# Copyright 2015-2020 Tecnativa - Pedro M. Baeza
# Copyright 2016 Lorenzo Battistini
# Copyright 2016 Carlos Dauden <carlos.dauden@tecnativa.com>
# Copyright 2018 David Vidal <david.vidal@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Sale Order Type",
    "version": "16.0.1.1.0",
    "category": "Sales Management",
    "author": "Grupo Vermon,"
    "AvanzOSC,"
    "Tecnativa,"
    "Agile Business Group,"
    "Niboo,"
    "Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/sale-workflow",
    "license": "AGPL-3",
    "depends": ["sale_stock", "account", "sale_management"],
    "demo": ["demo/sale_order_demo.xml"],
    "data": [
        "security/ir.model.access.csv",
        "security/security.xml",
        "views/sale_order_view.xml",
        "views/sale_order_type_view.xml",
        "views/account_move_views.xml",
        "views/res_partner_view.xml",
        "data/default_type.xml",
        "reports/account_invoice_report_view.xml",
        "reports/sale_report_view.xml",
    ],
    "installable": True,
}
