{
    'name': 'VendAI Base',
    'version': '1.0',
    'category': 'Sales/Point of Sale',
    'sequence': 1,
    'summary': 'AI-Powered Point of Sale for Small Retail',
    'description': """
        Transform your shop with VendAI - an intelligent Point of Sale system
        that helps you manage inventory, sales, and suppliers effortlessly.
    """,
    'depends': [
        'base',
        'web',
        'point_of_sale',
        'stock',
        'purchase',
        'account',
    ],
    'data': [
        'security/vendai_security.xml',
        'security/ir.model.access.csv',
        'views/vendai_views.xml',
        'views/onboarding_views.xml',
        'views/pos_config_views.xml',
        'data/vendai_data.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'vendai_base/static/src/js/vendai_assistant.js',
            'vendai_base/static/src/js/onboarding.js',
            'vendai_base/static/src/scss/vendai_style.scss',
        ],
        'point_of_sale.assets': [
            'vendai_base/static/src/js/pos_extension.js',
        ],
    },
    'application': True,
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
