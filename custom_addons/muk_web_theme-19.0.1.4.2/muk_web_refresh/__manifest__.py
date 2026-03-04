{
    'name': 'MuK Web Refresh', 
    'summary': 'Refresh views manually, automatically, or from the backend',
    'description': '''
        Adds a refresh button to reload the current view with a single
        click. Double-click the button to toggle auto refresh, which
        reloads the view every 30 seconds. Configure automation rules
        with the Reload Views action type to trigger view refreshes
        from the backend via the bus.
    ''',
    'version': '19.0.1.1.1',
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
        'bus',
        'base_automation',
    ],
    'data': [
        'views/ir_actions_server_views.xml',
    ],
    'demo': [
        'demo/base_automation.xml',
        'demo/ir_actions_server.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'muk_web_refresh/static/src/core/utils.js',
            'muk_web_refresh/static/src/scss/refresh.scss',
            (
                'after',
                'web/static/src/search/control_panel/control_panel.js',
                'muk_web_refresh/static/src/search/control_panel.js',
            ),            
            (
                'after',
                'web/static/src/search/control_panel/control_panel.xml',
                'muk_web_refresh/static/src/search/control_panel.xml',
            ),
            'muk_web_refresh/static/src/services/refresh_service.js',
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
