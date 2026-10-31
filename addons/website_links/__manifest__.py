{
    'name': 'Link Tracker',
    'category': 'Website/Website',
    'summary': 'Generate trackable & short URLs',
    'description': """
Generate short links with analytics trackers (UTM) to share your pages through marketing campaigns.
Those trackers can be used in Google Analytics to track clicks and visitors, or in Odoo reports to analyze the efficiency of those campaigns in terms of lead generation, related revenues (sales orders), recruitment, etc.
    """,
    'depends': ['website', 'link_tracker'],
    'data': [
        'views/link_tracker_views.xml',
        'views/website_links_template.xml',
        'views/website_links_graphs.xml',
        'security/ir.access.csv',
    ],
    'auto_install': True,
    'assets': {
        'web.assets_backend': [
            'website_links/static/src/components/fields/**/*',
        ],
        'web.assets_frontend': [
            'website_links/static/src/components/*.js',
            'website_links/static/src/interactions/*.js',
            'website_links/static/src/css/website_links.css',
            'website_links/static/src/xml/*.xml',
        ],
        'website.assets_editor': [
            'website_links/static/src/components/dialog/*.js',
            'website_links/static/src/components/dialog/*.xml',
            'website_links/static/src/services/website_custom_menus.js',
        ],
        'web.assets_tests': [
            'website_links/static/tests/tours/**/*',
        ],
        'web.assets_unit_tests': [
            'website_links/static/tests/url_autocomplete.test.js',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
