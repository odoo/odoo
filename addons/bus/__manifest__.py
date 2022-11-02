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
            'bus/static/src/setup/core/*.js',
            'bus/static/src/setup/common/*.js',
            'bus/static/src/setup/backend/*.js',
        ],
        'web.assets_frontend': [
            'bus/static/src/*.js',
            'bus/static/src/services/**/*.js',
            ('remove', 'bus/static/src/services/assets_watchdog_service.js'),
            'bus/static/src/workers/websocket_worker.js',
            'bus/static/src/workers/websocket_worker_utils.js',
            'bus/static/src/setup/core/*.js',
            'bus/static/src/setup/common/*.js',
            'bus/static/src/setup/frontend/*.js',

        ],
        'web.qunit_suite_tests': [
            'bus/static/tests/**/*.js',
        ],
        'web.qunit_mobile_suite_tests': [
            'bus/static/tests/helpers/**/*.js',
        ],
        'bus.websocket_worker_assets': [
            'web/static/src/legacy/js/promise_extension.js',
            'web/static/src/boot.js',
            'bus/static/src/workers/*',
        ],
    },
    'license': 'LGPL-3',
}
