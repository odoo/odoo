{
    'name': 'Library Management',
    'category': 'Library',
    'summary': 'Manage books, members and borrowing in a small library',
    'description': """
Library Management
===================
A simple module to demonstrate custom Odoo module development.

Features
--------
* Manage books with author, ISBN and availability state
* Manage library members
* Borrow / return workflow
""",
    'author': 'Odoo Training',
    'license': 'LGPL-3',
    'depends': ['base'],
    'data': [
        'security/ir.access.csv',
        'views/library_book_views.xml',
        'views/library_member_views.xml',
        'views/library_menus.xml',
    ],
    'demo': [
        'data/library_demo.xml',
    ],
    'application': True,
    'installable': True,
}
