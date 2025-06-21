{
    'name': 'Barcode',
    'version': '2.0',
    'category': 'Hidden',
    'summary': 'Scan and Parse Barcodes',
    'depends': ['web'],
    'data': [
        'data/barcodes_data.xml',
        'views/barcodes_view.xml',
        'security/ir.model.access.csv',
        ],
    'installable': True,
    'post_init_hook': '_assign_default_nomeclature_id',
    'assets': {
        'web.assets_backend': [
            'barcodes/static/src/**/*',
        ],
        'web.tests_assets': ['barcodes/static/tests/helpers.js'],
        'web.qunit_suite_tests': ['barcodes/static/tests/basic/**/*.js'],
        'web.qunit_mobile_suite_tests': ['barcodes/static/tests/mobile/*.js'],
    },
    'license': 'LGPL-3',
}
