{
    'name': 'Test ORM',
    'category': 'Hidden/Tests',
    'description': """A module to test the ORM.""",
    'depends': ['base'],
    'data': [
        'data/test_translated_field/test_model_data.xml',
        'data/ir_asset.xml',
        'data/test_access_rights_data.xml',
        'data/test_action_bindings.xml',
        'data/test_inherits.xml',
        'data/test_orm_data.xml',
        'data/test_orm_partner.xml',
        'views/test_acl.xml',
        'views/test_orm_views.xml',
        'views/views.xml',
        'security/ir.access.csv',
    ],
    'assets': {
        'web.assets_tests': [
            'test_base/static/tests/test_css_error.js',
        ],
        'test_assetsbundle.bundle2': [
            'test_base/static/src/css/test_cssfile1.css',
        ],
        'test_assetsbundle.bundle3': [
            'test_base/static/src/scss/test_file1.scss',
        ],
        'test_assetsbundle.bundle4': [
                'test_base/static/src/js/test_jsfile1.js',
                'test_base/static/src/js/test_jsfile2.js',
                'http://test.external.link/javascript1.js',

                'test_base/static/src/css/test_cssfile1.css',
                'http://test.external.link/style1.css',
                'test_base/static/src/css/test_cssfile2.css',

                'test_base/static/src/js/test_jsfile3.js',
                'http://test.external.link/javascript2.js',

                'http://test.external.link/style2.css',
        ],
        'test_assetsbundle.manifest1': [
            'test_base/static/src/*/**',
        ],
        'test_assetsbundle.manifest2': [
            'test_base/static/src/js/test_jsfile1.js',
            'test_base/static/src/*/**',
        ],
        'test_assetsbundle.manifest3': [
            'test_base/static/src/js/test_jsfile3.js',
            'test_base/static/src/*/**',
        ],
        'test_assetsbundle.manifest4': [
            'test_base/static/src/js/test_jsfile3.js',
        ],
        'test_assetsbundle.manifest5': [
            'test_base/static/src/js/test_jsfile1.js',
            'test_base/static/src/js/test_jsfile2.js',
            'test_base/static/src/js/test_jsfile3.js',
            'test_base/static/src/js/test_jsfile4.js',
        ],
        'test_assetsbundle.manifest6': [
            ('include', 'test_assetsbundle.manifest4'),
        ],
        'test_assetsbundle.manifest_multi_module1': [],
        'test_assetsbundle.broken_css': [
            'test_base/static/invalid_src/css/invalid_css.css',
        ],
        'test_assetsbundle.lazy_test_component': [
            'test_base/static/tests/lazy_test_component/**/*',
        ],
        'test_assetsbundle.broken_xml': [
            'test_base/static/invalid_src/xml/invalid_xml.xml',
        ],
        'test_assetsbundle.multiple_broken_xml': [
            'test_base/static/invalid_src/xml/invalid_xml.xml',
            'test_base/static/invalid_src/xml/second_invalid_xml.xml',
        ],
        'test_assetsbundle.multiple_same_name':[
          'test_base/static/invalid_src/xml/multiple_same_name.xml',
        ],
        'test_assetsbundle.wo_name':[
          'test_base/static/invalid_src/xml/template_wo_name.xml',
        ],
        'test_assetsbundle.file_not_found':[
          'test_base/static/invalid_src/xml/file_not_found.xml',
        ],
        'web.assets_unit_tests': [
            'test_base/static/tests/lazy_component.test.js',
        ],
    },
    'other_files': [
        'data/test_translated_field/test_tools.convert.csv',
    ],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
