{
    'name': 'Website',
    'category': 'CMS',
    'version': '1.0',
    'description': """
OpenERP Website CMS
===================

        """,
    'author': 'OpenERP SA',
    'depends': ['base'],
    'installable': True,
    'data': [
        'views/views.xml'
     ],
    'js': [
        'static/src/js/website.js',
    ],
    'css': [
        'static/src/css/*.css',
    ],
    'qweb': ['static/src/xml/*.xml'],
}
