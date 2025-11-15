{
    'name': 'OneDesk Core',
    'version': '1.0.0',
    'summary': 'Core of OneDesk (central hub for property management, tasks, documents, etc.)',
    'author': 'Merveilles',
    'license': 'LGPL-3',
    'category': 'Services',
    'depends': ['base', 'contacts', 'mail', 'account', 'calendar'],  # ← Ajouté 'calendar'
    'data': [
    'security/ir.model.access.csv',

    # Vues (charger les vues avant les données pour éviter les erreurs)
    'views/onedesk_dashboard_views.xml',
    'views/onedesk_amenity_views.xml',
    'views/onedesk_property_views.xml',
    'views/onedesk_unit_views.xml',
    'views/onedesk_reservation_views.xml',
    'views/onedesk_task_views.xml',
    'views/onedesk_integration_provider_views.xml',
    'views/onedesk_integration_views.xml',
    'views/onedesk_integration_menu.xml',
    'views/oauth_templates.xml',
    'views/onedesk_menu_views.xml',

    # Données (après les vues)
    'data/onedesk_amenity_data.xml',
    'data/integration_providers.xml',
    'data/integration_cron.xml',
    'data/email_templates.xml',
    ],
    
    # ← NOUVEAU : Dépendances Python
    'external_dependencies': {
        'python': ['cryptography', 'requests'],
    },
    
    'installable': True,
    'application': True,
}

