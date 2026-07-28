# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'My Custom Table Module',  # The name of the module displayed in Odoo
    'version': '1.0',  # Initial version
    'summary': 'A simple module to create a custom database table.',  # A short summary
    'description': """
This module defines a simple data model which results in a new database table
being created when the module is installed.
    """,
    'author': 'Aayush Jain',  # Put your name here
    'website': 'http://www.localhost:8069',  # Optional website
    'category': 'Uncategorized',  # Choose an appropriate category
    'depends': [
        'base',  # Every module typically depends on 'base'
        ],
    'data': [
        # We don't have views or data files in this simple example yet
        # 'security/ir.model.access.csv', # You would add security rules here
        # 'views/my_simple_model_views.xml', # You would add views here
    ],
    'installable': True,  # Allows the module to be installed
    'application': False, # Is this a main application (shows up in main Apps filter)?
    'auto_install': False, # Should it install automatically if dependencies are met?
    'license': 'LGPL-3', # Specify the license
}
