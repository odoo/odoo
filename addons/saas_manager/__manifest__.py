{
    'name': 'SaaS Manager',
    'version': '1.0',
    'summary': 'Gestion des clients SaaS Odoo',
    'description': """
        Création automatisée d'instances Odoo
        Gestion des packs modulaires
    """,
    'author': 'Alain GANSONRE',
    'depends': ['base'],
    'data': [
        'views/client_views.xml',
        #'views/pack_views.xml',
    ],
    'installable': True,
    'application': True,
}