{
    'name': 'Link Tracker',
    'category': 'Hidden',
    'description': """
Create short and trackable URLs.
=====================================================

        """,
    'version': '1.0',
    'depends':['website','marketing', 'utm'],
    'data' : [
        'views/website_links.xml',
        'views/website_links_template.xml',
        'views/website_links_graphs.xml',
        'security/ir.model.access.csv',
    ],
    'qweb': ['static/src/xml/*.xml'],
    'auto_install': True,
}
