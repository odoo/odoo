{
    'name': 'Website',
    'category': 'Website',
    'summary': 'Create Your Enterprise Website',
    'version': '1.0',
    'description': """
OpenERP Website CMS
===================

        """,
    'author': 'OpenERP SA',
    'depends': ['web'],
    'installable': True,
    'data': [
        'views/views.xml',
        'views/themes.xml',
        'views/res_config.xml',
        'website_data.xml',
    ],
}
