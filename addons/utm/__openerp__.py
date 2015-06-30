{
    'name': 'UTM Trackers',
    'category': 'Hidden',
    'description': """
Enable UTM trackers in shared links.
=====================================================
        """,
    'version': '1.0',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'views/utm.xml',
        'data/utm_data.xml'
    ],
    'demo': [],
    'auto_install': True,
}
