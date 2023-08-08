# Copyright 2022, Jarsa Sistemas, S.A. de C.V.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

{
    "name": "Report Sale Order trinitate",
    "summary": """
        Wizard to be able to redirect to the sales order report.""",
    "version": "15.0.1.0.0",
    "category": "Sale Order",
    "author": "Jarsa",
    "website": "https://www.jarsa.com.mx",
    "license": "LGPL-3",
    "depends": [
        "sale",
        "contacts",
        "operating_unit",
        "base_address_extended",
        "base_address_city",
    ],
    "data": [
        "security/res_groups_data.xml",
        "security/ir_rule_data.xml",
        "security/ir.model.access.csv",
        "wizards/wizard_report_sale_order_view.xml",
        "views/sale_order_report_views.xml",
        "views/res_user_view.xml",
    ],
}
