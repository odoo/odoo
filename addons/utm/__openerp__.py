{
    'name': 'UTM Trackers',
    'category': 'Hidden',
    'description': """
Enable UTM trackers in shared links.
=====================================================
        """,
    'version': '1.0',
    'depends':['marketing'],
    'data' : [
        'security/ir.model.access.csv',
        'views/utm.xml',
    ],
    'demo': ['utm_demo.xml'],
    'auto_install': True,
}
