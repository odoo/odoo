# -*- coding: utf-8 -*-
{
    'name': 'Simple Library',
    'version': '18.0.1.0',
    'summary': 'A very basic library management module.',
    'description': """
        Minimal example module demonstrating core Odoo concepts:
        - Model definition
        - Views (Tree, Form)
        - Menus and Actions
        - Basic Security
        - Controller with JSON route
        - Extending an existing model (res.partner)
    """,
    'author': 'Prithvi',
    'website': 'https://www.example.com',
    'category': 'Knowledge',
    'depends': [
        'base', # Implicit dependency, good practice to list
        'web',  # Needed for controllers
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/library_menus.xml', # Load menus & actions first
        'views/library_book_views.xml',
        'views/res_partner_views.xml', # Load partner view extension
    ],
    'installable': True,
    'application': True, # Makes it appear as an App in the Apps menu
    'license': 'LGPL-3',
}