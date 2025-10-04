{
    'name' : 'IM Bus',
    'version': '1.0',
    'category': 'Hidden',
    'description': "Instant Messaging Bus allow you to send messages to users, in live.",
    'depends': ['base', 'web'],
    'data': [
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'auto_install': True,
    'assets': {
        'web.assets_backend': [
            'bus/static/src/*.js',
            'bus/static/src/services/**/*.js',
            'bus/static/src/workers/websocket_worker.js',
            'bus/static/src/workers/websocket_worker_utils.js',
        ],
        'web.assets_frontend': [
            'bus/static/src/*.js',
            'bus/static/src/services/**/*.js',
            ('remove', 'bus/static/src/services/assets_watchdog_service.js'),
            ('remove', 'bus/static/src/simple_notification_service.js'),
            'bus/static/src/workers/websocket_worker.js',
            'bus/static/src/workers/websocket_worker_utils.js',
        ],
        'web.tests_assets': [
            'bus/static/tests/helpers/**/*',
        ],
        'web.qunit_suite_tests': [
            'bus/static/tests/**/*.js',
            ('remove', 'bus/static/tests/helpers/**/*'),
        ],
        'bus.websocket_worker_assets': [
            'web/static/src/module_loader.js',
            'bus/static/src/workers/*',
        ],
    },
    'license': 'LGPL-3',
}
