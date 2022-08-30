# JUAN PABLO YAÑEZ CHAPITAL
{
    "name": "Export Pricelist",
    "author": "JUAN PABLO YAÑEZ CHAPITAL",
    "support": "compraschapital@hotmail.com",
    "website": "https://www.chapital.com.mx",
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

    "auto_install": False,
    "application": True,
    "installable": True,
    "price": 0,
    "currency": "EUR"
}
