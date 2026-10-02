{
    "name": "Sale Order Split",
    "summary": "Split a sale order in sub-sale order based on options",
    "version": "16.0.1.0.1",
    "category": "Sales/Sales",
    "author": "BizzAppDev Systems Pvt. Ltd.",
    "website": "http://www.bizzappdev.com",
    "license": "AGPL-3",
    "depends": ["sale_management"],
    "data": [
        "security/ir.model.access.csv",
        "wizard/sale_order_split_quotation_view.xml",
        "views/sale_order_view.xml",
    ],
}
