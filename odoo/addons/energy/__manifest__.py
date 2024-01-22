{
    "name": "Energy Trading",  # The name that will appear in the App list
    "version": "1.0",  # Version
    "application": True,  # This line says the module is an App, and not a module
    "depends": [  # dependencies
        "base",
        "web_widget_x2many_2d_matrix",
    ],
    "installable": True,
    'license': 'LGPL-3',
    'external_dependencies': {
        'python': ['pandas']
    },
    'data': [
        'data/ir_sequence_data.xml',
        'wizard/energy_distribution_wizard_views.xml',
        'views/company_views.xml',
        'views/payment_terms_views.xml',
        'views/voltage_views.xml',
        'views/distribution_details_views.xml',
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
        'security/ir.model.access.csv',
    ],
    'assets': {
        'web.assets_backend': [
            'energy/static/src/js/loadshape_details.js',
            'energy/static/src/js/form_controller_extension.js',

        ],
    },
    'category': 'Productivity'
}
