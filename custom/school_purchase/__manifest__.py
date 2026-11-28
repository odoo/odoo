{
    "name": "School Purchase",
    "version": "19.0.1.2.1",
    "category": "Inventory/Purchase",
    "summary": "Class textbook procurement with stock-aware RFQ generation",
    "description": "Computes book requirements per class section, respects available free stock, and creates draft purchase RFQs grouped by vendor.",
    "author": "Harvard University",
    "depends": [
        "purchase_stock",
        "school_management",
    ],
    "data": [
        "security/procurement/ir.model.access.csv",
        "security/procurement/book_procurement_security.xml",
        "views/procurement/class_book_purchase_views.xml",
        "views/procurement/book_requirement_views.xml",
    ],
    "pre_init_hook": "pre_init_hook",
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
