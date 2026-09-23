{
    "name": "Romania - CPV Code",
    "version": "1.0",
    "category": "Hidden",
    "description": """
This is the module to add CPV (Common Procurement Vocabulary) identification number on product.
The Romanian CIUS-RO format requires, in some case, the precise categorisation of products sold to be included in the details of the line of an invoice.
    """,
    "author": "Odoo",
    "license": "LGPL-3",
    "depends": [
        "l10n_ro_edi",
    ],
    "data": [
        "data/l10n_ro.cpv.code.csv",
        "views/product_views.xml",
        "security/ir.access.csv",
    ],
}
