{
    'name' : 'IM Bus',
    'version': '1.0',
    'category': 'Hidden',
    'complexity': 'easy',
    'description': "Instant Messaging Bus allow you to send messages to users, in live.",
    'depends': ['base', 'web'],
    'data': [
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'assets': {
        'bus.server_communication_shared_worker': [
            'bus/static/src/server_communication_shared_worker/main.js',
        ],
        'web.assets_common': [
            'bus/static/src/js/main.js',
            'bus/static/src/services/crosstab_communication.js',
            'bus/static/src/services/localstorage_communication.js',
            'bus/static/src/services/longpolling_communication.js',
            'bus/static/src/services/server_communication.js',
            'bus/static/src/services/sharedworker_communication.js',
            'bus/static/src/services/user_presence.js',
        ],
        'web.qunit_suite_tests': [
            'bus/static/tests/bus_tests.js',
        ],
        'web.assets_tests': [
            'bus/static/tests/bus_tests_tour.js',
        ],
    }
}
