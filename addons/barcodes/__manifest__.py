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
    'auto_install': False,
    'post_init_hook': '_assign_default_nomeclature_id',
    'assets': {
        'web.assets_backend': [
            'barcodes/static/src/**/*',
        ],
        'web.qunit_suite_tests': [
            'barcodes/static/tests/barcode_tests.js',
            'barcodes/static/tests/barcode_parser_tests.js',
        ],
        'web.qunit_mobile_suite_tests': [
            'barcodes/static/tests/barcode_mobile_tests.js',
        ],
    },
    'license': 'LGPL-3',
}
