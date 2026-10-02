# Copyright 2020 Tecnativa - Manuel Calero
# Copyright 2022 Quartile
# Copyright 2014-2022 Tecnativa - Pedro M. Baeza
{
    "name": "Commissions",
    "version": "16.0.2.3.0",
    "author": "Tecnativa, Odoo Community Association (OCA)",
    "category": "Invoicing",
    "license": "AGPL-3",
    "depends": ["product"],
    "website": "https://github.com/OCA/commission",
    "maintainers": ["pedrobaeza"],
    "data": [
        "security/commission_security.xml",
        "security/ir.model.access.csv",
        "data/menuitem_data.xml",
        "views/commission_views.xml",
        "views/commission_settlement_views.xml",
        "views/commission_mixin_views.xml",
        "views/product_template_views.xml",
        "views/res_partner_views.xml",
        "reports/commission_settlement_report.xml",
        "reports/report_settlement_templates.xml",
        "wizards/commission_make_settle_views.xml",
    ],
    "demo": ["demo/commission_and_agent_demo.xml"],
    "installable": True,
}
