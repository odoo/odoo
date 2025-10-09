{
    'name': "Purchase Requisitions",

    'summary': """
         Purchase Requisitions""",

    'description': """
         Purchase Requisitions
    """,

    'author': "Immy",

    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','purchase','hr','stock'],

    # always loaded
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/po_requisition_view.xml',
        'views/bid.xml',
        'views/menus.xml',
    ],
}