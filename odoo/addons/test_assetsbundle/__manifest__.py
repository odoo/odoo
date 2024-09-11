# -*- coding: utf-8 -*-
{
    'name': 'test-assetsbundle',
    'version': '0.1',
    'category': 'Hidden/Tests',
    'description': """A module to verify the Assets Bundle mechanism.""",
    'depends': ['base'],
    'installable': True,
    'data': [
        "data/ir_asset.xml",
        "views/views.xml",
    ],

    'assets': {
        'test_assetsbundle.bundle2': [
            'test_assetsbundle/static/src/css/test_cssfile1.css',
        ],
        'test_assetsbundle.bundle3': [
            'test_assetsbundle/static/src/scss/test_file1.scss',
        ],
        'test_assetsbundle.bundle4': [
                'test_assetsbundle/static/src/js/test_jsfile1.js',
                'test_assetsbundle/static/src/js/test_jsfile2.js',
                'http://test.external.link/javascript1.js',

                'test_assetsbundle/static/src/css/test_cssfile1.css',
                'http://test.external.link/style1.css',
                'test_assetsbundle/static/src/css/test_cssfile2.css',

                'test_assetsbundle/static/src/js/test_jsfile3.js',
                'http://test.external.link/javascript2.js',

                'http://test.external.link/style2.css',
        ],
        'test_assetsbundle.manifest1': [
            'test_assetsbundle/static/src/*/**',
        ],
        'test_assetsbundle.manifest2': [
            'test_assetsbundle/static/src/js/test_jsfile1.js',
            'test_assetsbundle/static/src/*/**',
        ],
        'test_assetsbundle.manifest3': [
            'test_assetsbundle/static/src/js/test_jsfile3.js',
            'test_assetsbundle/static/src/*/**',
        ],
        'test_assetsbundle.manifest4': [
            'test_assetsbundle/static/src/js/test_jsfile3.js',
        ],
        'test_assetsbundle.manifest5': [
            'test_assetsbundle/static/src/js/test_jsfile1.js',
            'test_assetsbundle/static/src/js/test_jsfile2.js',
            'test_assetsbundle/static/src/js/test_jsfile3.js',
            'test_assetsbundle/static/src/js/test_jsfile4.js',
        ],
        'test_assetsbundle.manifest6': [
            ('include', 'test_assetsbundle.manifest4'),
        ],
        'test_assetsbundle.manifest_multi_module1': [],
        'test_assetsbundle.broken_css': [
            'test_assetsbundle/static/invalid_src/css/invalid_css.css',
        ],
        'test_assetsbundle.lazy_test_component': [
            'test_assetsbundle/static/tests/lazy_test_component/**/*',
        ],
    },
    'license': 'LGPL-3',
}
