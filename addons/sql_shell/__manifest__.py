{
    'name': 'SQL Shell',
    'version': '1.0',
    'category': 'Hidden/Tools',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'views/sql_shell_views.xml',
    ],
    'installable': True,
    'license': 'LGPL-3',
    'assets': {
        'web.assets_backend': [
            'sql_shell/static/src/**/*',
        ],
    }
}
