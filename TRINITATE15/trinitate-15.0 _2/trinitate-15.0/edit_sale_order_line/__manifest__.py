# Copyright 2022 Jarsa
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl).
{
    "name": "Edit product sale order line",
    "summary": """
    can or not edit product in sale order line
    """,
    "author": "Jarsa",
    "website": "https://www.jarsa.com",
    "license": "LGPL-3",
    "category": "Installer",
    "version": "15.0.1.0.1",
    "depends": ["trinitate"],
    "test": [],
    "data": [
        "security/res_groups_data.xml",
        "views/product_template_view.xml",
        "views/sale_order_view.xml",
        "security/ir_model_acces.csv",
        
    ],
    "demo": [],
    "installable": True,
    "auto_install": False,
    "application": True,
}
