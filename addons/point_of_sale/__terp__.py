# -*- encoding: utf-8 -*-
{
    "name": "Point Of Sale",
    "version": "1.0",
    "author": "Tiny",

    "description": """
Main features :
 - Fast encoding of the sale.
 - Allow to choose one payment mode (the quick way) or to split the payment between several payment mode.
 - Computation of the amount of money to return.
 - Create and confirm picking list automatically.
 - Allow the user to create invoice automatically.
 - Allow to refund former sales.

    """,
    "category": "Generic Modules/Sales & Purchases",
    "depends": ["sale", "purchase", "account", "account_tax_include"],
    "init_xml": [],
    "demo_xml": [],
    "update_xml": [
        "security/point_of_sale_security.xml",
        "security/ir.model.access.csv",
        "pos_report.xml", "pos_wizard.xml",
        "pos_view.xml", "pos_sequence.xml", 
        "pos_data.xml", "pos_workflow.xml"
    ],
    "installable": True,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

