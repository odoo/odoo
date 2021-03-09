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
        'web.assets_backend': [
            # inside .
            'bus/static/src/js/longpolling_bus.js',
            # inside .
            'bus/static/src/js/crosstab_bus.js',
            # inside .
            'bus/static/src/js/services/bus_service.js',
            # inside .
            'bus/static/src/js/web_client_bus.js',
        ],
        'web.assets_frontend': [
            # inside .
            'bus/static/src/js/longpolling_bus.js',
            # inside .
            'bus/static/src/js/crosstab_bus.js',
            # inside .
            'bus/static/src/js/services/bus_service.js',
        ],
        'web.qunit_suite_tests': [
            # after //script[last()]
            'bus/static/tests/bus_tests.js',
        ],
        'web.assets_tests': [
            # inside .
            'bus/static/tests/bus_tests_tour.js',
        ],
    }
}
