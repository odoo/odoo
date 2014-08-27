{
    'name': 'Website Forum SEO',
    'category': 'Website',
    'summary': 'Website forum SEO keyword',
    'version': '1.0',
    'description': """
Replace keyword to a highlighted word
=====================================

        """,
    'author': 'OpenERP SA',
    'depends': ['website_forum', 'marketing'],
    'data': [
        'views/forum_seo.xml',
        'security/ir.model.access.csv',
    ],
    'demo': [
        'data/forum_seo_demo.xml'
    ],
    'qweb': [],
    'installable': True,
    'application': False,
}
