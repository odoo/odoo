# -*- coding: utf-8 -*-
{
    'name': 'Gestion Fiches',
    'version': '1.0',
    'summary': 'Module pour la gestion des fiches avec inscription utilisateurs',
    'description': """
        Ce module permet de gérer les fiches et propose un formulaire 
        d'inscription pour les utilisateurs (Techniciens, Commerciaux, Secrétaires).
    """,
    'author': 'Ton Nom ou Entreprise',
    'website': 'https://www.tonsite.com',
    'category': 'Custom',
    'depends': [
        'base',      
        'website',    
        'mail', 
        'sale',      
    ],
    'data': [
        #'views/produit_commission_views.xml',
        #'views/menus.xml',
        #'views/templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            #'gestion_fiches/static/src/css/style.css',  # Ton CSS personnalisé (si besoin)
            #'gestion_fiches/static/src/js/script.js',   # Ton JS personnalisé (si besoin)
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
