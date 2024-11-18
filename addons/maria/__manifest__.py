# -*- coding: utf-8 -*-
{
    'name': "Maria",

    'summary': "Gestion de projets Agile dans Odoo",

    'description': """
Module de gestion de projets Agile pour Odoo.
Ce module permet de gérer les projets en utilisant des méthodologies Agile comme Scrum et Kanban.
    """,

    'author': "Mariatouil",
    'website': "https://www.odoo.com/app/project",
    'license': 'AGPL-3',  # Indiquer la licence sous laquelle le module est distribué
    'installable': True,  # Permet d'installer le module
    'application': True,  
   
    'category': 'Project Management',
    'version': '0.1.0',  # Suivre le versionnage sémantique

    # any module necessary for this one to work correctly
    'depends': ['base', 'project'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',  # Décommenté pour gérer les permissions
        'views/views.xml',
        'views/templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
