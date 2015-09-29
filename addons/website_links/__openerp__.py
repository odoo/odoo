{
    'name': 'Website Link Tracker',
    'category': 'Hidden',
    'description': """
Website interface to create short and trackable URLs.
=====================================================

        """,
    'version': '1.0',
    'depends': ['website', 'marketing', 'link_tracker'],
    'data': [
        'views/website_links_template.xml',
        'views/website_links_graphs.xml',
        'security/ir.model.access.csv',
    ],
    'qweb': ['static/src/xml/*.xml'],
    'auto_install': True,
}
