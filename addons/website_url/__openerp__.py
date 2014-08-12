{
    'name': 'Website URl',
    'category': 'Hidden',
    'description': """
To shorten URL and To show url click statistics.
=====================================================

        """,
    'version': '2.0',
    'depends':['website','marketing'],
    'data' : [
        'views/website_url.xml',
        'security/ir.model.access.csv',
    ],
    'qweb': [],
    'auto_install': True,
}
