{
    'name': 'MuK Groups', 
    'summary': 'Adds expand/collapse for views',
    'description': '''
        Enables you to expand and collapse groups that were created by 
        grouping the data by a certain field for list and kanban views.
    ''',
    'version': '19.0.1.0.0',
    'category': 'Tools/UI',
    'license': 'LGPL-3', 
    'author': 'MuK IT',
    'website': 'http://www.mukit.at',
    'live_test_url': 'https://youtu.be/XiMde7ROg-kS',
    'contributors': [
        'Mathias Markl <mathias.markl@mukit.at>',
    ],
    'depends': [
        'web',
    ],
    'assets': {
        'web.assets_backend': [
            '/muk_web_group/static/src/**/*',
        ],
        'web.assets_unit_tests': [
            'muk_web_group/static/tests/**/*',
        ],
    },
    'images': [
        'static/description/banner.png',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
