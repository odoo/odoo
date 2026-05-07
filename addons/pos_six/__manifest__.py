{
    'name': 'POS Six',
    'category': 'Sales/Point Of Sale',
    'sequence': 6,
    'summary': 'Integrate your POS with a Six payment terminal',
    'data': [
        'views/pos_payment_method_views.xml',
    ],
    'depends': ['point_of_sale'],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
    'assets': {
        'point_of_sale._assets_pos': [
            ('prepend', 'pos_six/static/src/app/timapi_loader.js'),
            'pos_six/static/lib/six_timapi/*',
            'pos_six/static/src/**/*',
        ],
        'point_of_sale.payment_terminals': [
            'pos_six/static/src/app/payment_six.js',
        ],
        'web.assets_unit_tests_setup': [
            # `timapi` is the vendored SIX SDK; it eagerly fetches its `.wasm`
            # at script-eval time, which 404s under the test runner. Tests stub
            # `window.timapi` directly, so the real SDK is not needed.
            ('remove', 'pos_six/static/lib/six_timapi/timapi.js'),
        ],
        'web.assets_unit_tests': [
            'pos_six/static/tests/unit/**/*',
        ],
    }
}
