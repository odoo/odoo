{
    'name': 'MuK Web Refresh', 
    'summary': 'Automatically refresh any list or kanban view',
    'description': '''
        Activate the auto refresh button to reload the view every
        30 seconds. The refresh will reload and update the data
        of the view.
    ''',
    'version': '19.0.1.0.0',
    'category': 'Tools/UI',
    'license': 'LGPL-3', 
    'author': 'MuK IT',
    'website': 'http://www.mukit.at',
    'live_test_url': 'https://youtu.be/LmDAgBBWZBQ',
    'contributors': [
        'Mathias Markl <mathias.markl@mukit.at>',
    ],
    'depends': [
        'web',
    ],
    'assets': {
        'web.assets_backend': [            
            (
                'after',
                '/web/static/src/search/control_panel/control_panel.js',
                '/muk_web_refresh/static/src/search/control_panel.js',
            ),            
            (
                'after',
                '/web/static/src/search/control_panel/control_panel.xml',
                '/muk_web_refresh/static/src/search/control_panel.xml',
            ),
        ],
        'web.assets_unit_tests': [
            'muk_web_refresh/static/tests/**/*',
        ],
    },
    'images': [
        'static/description/banner.png',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
