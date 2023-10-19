{
    "name": "Energy Trading",  # The name that will appear in the App list
    "version": "1.0",  # Version
    "application": True,  # This line says the module is an App, and not a module
    "depends": ["base"],  # dependencies
    "installable": True,
    'license': 'LGPL-3',
    'data': [
        'views/company_views.xml',
        'views/voltage_views.xml',
        'views/contract_views.xml',
        'views/profile_views.xml',
        'views/period_views.xml',
        'views/loadshape_details_views.xml',
        'views/price_components_views.xml',
        'views/master_contract_views.xml',
        'views/profile_details_views.xml',
        'views/border_views.xml',
        'views/contract_prices_views.xml',
        'views/menu.xml',
        'security/ir.model.access.csv'
        
    ],
    'category': 'Productivity'
}