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
            "bus/static/src/bus_parameters_service.js",
            "bus/static/src/im_status_service.js",
            "bus/static/src/misc.js",
            "bus/static/src/multi_tab_service.js",
            "bus/static/src/services/bus_service.js",
            "bus/static/src/services/presence_service.js",
            'bus/static/src/workers/websocket_worker.js',
            'bus/static/src/workers/websocket_worker_utils.js',
        ],
        # Unit test files
        'web.assets_unit_tests': [
            'bus/static/tests/**/*',
            ('remove', 'bus/static/tests/legacy/**/*'), # to remove when all legacy tests are ported
        ],
        'web.tests_assets': [
            'bus/static/tests/legacy/helpers/**/*',
        ],
        'web.qunit_suite_tests': [
            'bus/static/tests/legacy/**/*.js',
            ('remove', 'bus/static/tests/legacy/helpers/**/*'),
        ],
        'bus.websocket_worker_assets': [
            'web/static/src/module_loader.js',
            'bus/static/src/workers/*',
        ],
    },
    'license': 'LGPL-3',
}
