# ©  2015-2018 Deltatech
# See README.rst file on addons root folder for license details


{
    "name": "Declaration of Conformity",
    "version": "14.0.1.0.0",
    "author": "Terrabit, Dorin Hongu",
    "license": "AGPL-3",
    "category": "Generic Modules/Other",
    "depends": [
        "base",
        "product",
        "sale",
        "mrp",
        # "stock_picking_invoice_link"
    ],
    "data": [
        "views/product_view.xml",
        "views/deltatech_dc_view.xml",
        "views/deltatech_dc_report.xml",
        "views/report_dc.xml",
        "security/ir.model.access.csv",
    ],
    "development_status": "stable",
    "maintainers": ["dhongu"],
}
