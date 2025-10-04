{
    'name': "smartclass",
    'summary': "This module can compute volumes and that's so great !",
    'depends': ['web', 'web_tour'],
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
    ],
    'assets': {
        "web.assets_backend": [
            "smartclass/static/src/**",
        ],
        'web.assets_tests': [
            'smartclass/static/tests/tours/**/*',
        ],
        'web.assets_unit_tests': [
            'smartclass/static/tests/**/*',
        ],
    },
    "application": True,
    'installable': True,
}

