# Copyright 2020 Tecnativa - Manuel Calero
# Copyright 2022 Quartile
# Copyright 2014-2022 Tecnativa - Pedro M. Baeza
{
    "name": "Account commissions",
    "version": "16.0.2.4.1",
    "author": "Tecnativa, Odoo Community Association (OCA)",
    "category": "Sales Management",
    "license": "AGPL-3",
    "depends": [
        "account",
        "commission",
    ],
    "website": "https://github.com/OCA/commission",
    "maintainers": ["pedrobaeza"],
    "data": [
        "security/account_commission_security.xml",
        "security/ir.model.access.csv",
        "data/menuitem_data.xml",
        "views/account_move_views.xml",
        "views/commission_settlement_views.xml",
        "views/commission_views.xml",
        "views/report_settlement_templates.xml",
        "report/commission_analysis_view.xml",
        "wizards/wizard_invoice.xml",
    ],
    "installable": True,
}
