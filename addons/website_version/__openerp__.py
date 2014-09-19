{
    'name': 'Website Versioning',
    'category': 'Website',
    'summary': 'Keep all the versions of your website',
    'version': '1.0',
    'description': """
OpenERP Website CMS
===================

        """,
    'author': 'OpenERP SA',
    'depends': ['website','marketing'],
    'installable': True,
    'data': [
        'security/ir.model.access.csv',
        'views/website_templates.xml',
        'views/marketing_view.xml',
        'views/website_views.xml',
        'views/res_config.xml',
        'data/demo.xml',
    ],
    'demo': [],
    'qweb': [],
    'application': True,
}