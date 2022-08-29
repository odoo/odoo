# Part of Softhealer Technologies.
{
    "name": "Export Pricelist",
    "author": "Softhealer Technologies",
    "support": "support@softhealer.com",
    "website": "https://www.softhealer.com",
    "license": "OPL-1",
    "category": "Extra Tools",
    "summary": "Export Pricelist,Export Customer Pricelist Module, Multiple Customer Pricelist App, PDF Multi Pricelist Application, Client Pricelist In Excel, Pricelist Export, Send Customer Pricelist Odoo",
    "description": """This module will provide feature to export a pricelist customer wise. You can get multiple customers pricelist in single PDF as well as in excel file(with different sheet).""",
    "version": "15.0.2",
    "depends": ["sale_management", "contacts","sh_product_brand"],
    "data": [
              'security/ir.model.access.csv',
              'views/sh_customer_pricelist_view.xml',
              'views/report_xlsx_view.xml',
              'views/sh_customer_details_report.xml',
    ],

    "images": ["static/description/background.png", ],
    "live_test_url": "https://www.youtube.com/watch?v=4NFlC6YFm7Q&feature=youtu.be",
    "auto_install": False,
    "application": True,
    "installable": True,
    "price": 35,
    "currency": "EUR"
}
