{
    'name': 'HOOT training',
    'category': 'Hidden',
    'version': '1.0',
    'license': 'LGPL-3',
    'description': """
HOOT training material
    """,
    'depends': ['web'],
    'installable': True,
    'auto_install': True,
    'assets': {
        'web.assets_backend': [
            'hoot_training/static/src/**/*',
        ],
        'web.assets_unit_tests': [
            'hoot_training/static/tests/**/*',
        ],
    },
}
