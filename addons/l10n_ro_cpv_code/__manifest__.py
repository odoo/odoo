{
    'name': 'Romania - CPV Code',
    'author': 'Odoo',
    'category': 'Hidden',
    'version': '1.0',
    'depends': ['l10n_ro_edi'],
    'description': """
This is the module to add CPV (Common Procurement Vocabulary) identification number on product.
The Romanian CIUS-RO format requires, in some case, the precise categorisation of products sold to be included in the details of the line of an invoice.
    """,
    'data': [
        'data/l10n_ro.cpv.code.csv',
        'views/product_views.xml',
        'security/ir.model.access.csv',
    ],
    "installable": True,
    'license': 'LGPL-3',
}
