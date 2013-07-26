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
        'views/views.xml',
        'views/res_config.xml',
        'website_data.xml',
     ],
    'js': [
        'static/lib/bootstrap/js/bootstrap.js',
        'static/src/js/website.js',
    ],
    'css': [
        'static/lib/bootstrap/css/bootstrap.css',
        'static/src/css/*.css',
    ],
    'qweb': ['static/src/xml/*.xml'],
}
