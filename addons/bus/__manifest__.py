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
            'bus/static/src/debug/**/*',
            'bus/static/src/services/**/*.js',
            'bus/static/src/workers/*',
            ('remove', 'bus/static/src/workers/bus_worker_script.js'),
        ],
        'web.assets_frontend': [
            'bus/static/src/*.js',
            'bus/static/src/services/**/*.js',
            ('remove', 'bus/static/src/services/assets_watchdog_service.js'),
            ('remove', 'bus/static/src/simple_notification_service.js'),
            'bus/static/src/workers/*',
            ('remove', 'bus/static/src/workers/bus_worker_script.js'),
        ],
        # Unit test files
        'web.assets_unit_tests': [
            'bus/static/tests/**/*',
        ],
        'bus.websocket_worker_assets': [
            'web/static/src/module_loader.js',
            'bus/static/src/workers/*',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
