{
    'name': 'Website Versioning',
    'category': 'Website',
    'summary': 'Allow to save all the versions of your website and allow to perform AB testing.',
    'version': '1.0',
    'description': """
OpenERP Website CMS
===================

        """,
    'author': 'OpenERP SA',
    'depends': ['website','marketing','google_account'],
    'installable': True,
    'data': [
        'security/ir.model.access.csv',
        'views/website_templates.xml',
        'views/marketing_view.xml',
        'views/website_views.xml',
        'views/res_config.xml',
        #'data/demo.xml',
        'data/data.xml',
    ],
    'demo': [],
    'qweb': ['static/src/xml/*.xml'],
    'application': True,
}