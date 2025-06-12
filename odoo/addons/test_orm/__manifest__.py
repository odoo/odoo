{
    'name': 'Test ORM',
    'version': '1.0',
    'category': 'Hidden/Tests',
    'description': """A module to test the ORM.""",
    'depends': ['base', 'web', 'web_tour'],
    'installable': True,
    'data': [
        'data/test_access_rights_data.xml',
        'data/test_action_bindings.xml',
        'data/test_assetsbundle.xml',
        'data/test_orm_data.xml',
        'data/test_translated_field/test_model_data.xml',
        'security/ir.model.access.csv',
        'security/test_access_rights_security.xml',
        'security/test_orm_security.xml',
        'views/test_assetsbundle_views.xml',
        'views/test_orm_views.xml',
    ],
    'assets': {
        'web.assets_tests': [
            'test_orm/static/tests/tours/constraint.js',
            'test_orm/static/tests/tours/x2many.js',
            'test_orm/static/tests/test_css_error.js',
        ],
        'test_orm.bundle2': [
            'test_orm/static/src/css/test_cssfile1.css',
        ],
        'test_orm.bundle3': [
            'test_orm/static/src/scss/test_file1.scss',
        ],
        'test_orm.bundle4': [
                'test_orm/static/src/js/test_jsfile1.js',
                'test_orm/static/src/js/test_jsfile2.js',
                'http://test.external.link/javascript1.js',

                'test_orm/static/src/css/test_cssfile1.css',
                'http://test.external.link/style1.css',
                'test_orm/static/src/css/test_cssfile2.css',

                'test_orm/static/src/js/test_jsfile3.js',
                'http://test.external.link/javascript2.js',

                'http://test.external.link/style2.css',
        ],
        'test_orm.manifest1': [
            'test_orm/static/src/*/**',
        ],
        'test_orm.manifest2': [
            'test_orm/static/src/js/test_jsfile1.js',
            'test_orm/static/src/*/**',
        ],
        'test_orm.manifest3': [
            'test_orm/static/src/js/test_jsfile3.js',
            'test_orm/static/src/*/**',
        ],
        'test_orm.manifest4': [
            'test_orm/static/src/js/test_jsfile3.js',
        ],
        'test_orm.manifest5': [
            'test_orm/static/src/js/test_jsfile1.js',
            'test_orm/static/src/js/test_jsfile2.js',
            'test_orm/static/src/js/test_jsfile3.js',
            'test_orm/static/src/js/test_jsfile4.js',
        ],
        'test_orm.manifest6': [
            ('include', 'test_orm.manifest4'),
        ],
        'test_orm.manifest_multi_module1': [],
        'test_orm.broken_css': [
            'test_orm/static/invalid_src/css/invalid_css.css',
        ],
        'test_orm.lazy_test_component': [
            'test_orm/static/tests/lazy_test_component/**/*',
        ],
        'test_orm.broken_xml': [
            'test_orm/static/invalid_src/xml/invalid_xml.xml',
        ],
        'test_orm.multiple_broken_xml': [
            'test_orm/static/invalid_src/xml/invalid_xml.xml',
            'test_orm/static/invalid_src/xml/second_invalid_xml.xml',
        ],
        'test_orm.multiple_same_name':[
          'test_orm/static/invalid_src/xml/multiple_same_name.xml',
        ],
        'test_orm.wo_name':[
          'test_orm/static/invalid_src/xml/template_wo_name.xml',
        ],
        'test_orm.file_not_found':[
          'test_orm/static/invalid_src/xml/file_not_found.xml',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
