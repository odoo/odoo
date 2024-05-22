{
    'name': 'Link Tracker',
    'category': 'Website/Website',
    'summary': 'Generate trackable & short URLs',
    'description': """
Generate short links with analytics trackers (UTM) to share your pages through marketing campaigns.
Those trackers can be used in Google Analytics to track clicks and visitors, or in Odoo reports to analyze the efficiency of those campaigns in terms of lead generation, related revenues (sales orders), recruitment, etc.
    """,
    'version': '1.0',
    'depends': ['website', 'link_tracker'],
    'data': [
        'views/link_tracker_views.xml',
        'views/website_links_template.xml',
        'views/website_links_graphs.xml',
        'security/ir.model.access.csv',
    ],
    'qweb': ['static/src/xml/*.xml'],
    'auto_install': True,
    'license': 'LGPL-3',
}
