{
    'name': 'URL Shortener',
    'category': 'Hidden',
    'description': """
To shorten URL and To show url click statistics.
=====================================================

        """,
    'version': '2.0',
    'depends':['website','marketing', 'crm'],
    'data' : [
        'views/website_url.xml',
        'views/website_url_template.xml',
        'views/website_url_graphs.xml',
        'security/ir.model.access.csv',
    ],
    'qweb': ['static/src/xml/*.xml'],
    'auto_install': True,
}
