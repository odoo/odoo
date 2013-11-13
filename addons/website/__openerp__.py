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
    'depends': ['web', 'share', 'select2'],
    'installable': True,
    'data': [
        'data/website_data.xml',
        'security/ir.model.access.csv',
        'views/website_templates.xml',
        'views/website_views.xml',
        'views/snippets.xml',
        'views/themes.xml',
    ],
    'demo': [
        'data/website_demo.xml',
    ]
}
