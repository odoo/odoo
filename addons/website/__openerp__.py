{
    'name': 'Website Builder',
    'category': 'Website',
    'summary': 'Build Your Enterprise Website',
    'version': '1.0',
    'description': """
OpenERP Website CMS
===================

        """,
    'author': 'OpenERP SA',
    'depends': ['web', 'share'],
    'installable': True,
    'css': ['static/lib/bootstrap-tour/css/website-tour.css'],
    'data': [
        'views/views.xml',
        'views/themes.xml',
        'views/res_config.xml',
        'website_data.xml',
        'website_view.xml',
        'security/ir.model.access.csv',
    ],
    'css': ['static/lib/bootstrap-tour/css/website-tour.css'],

}
