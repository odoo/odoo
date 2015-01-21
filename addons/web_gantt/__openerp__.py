{
    'name': 'Web Gantt',
    'category': 'Hidden',
    'description': """
Gantt chart client
==================

""",
    'version': '2.0',
    'depends': ['web'],
    'data' : [
        'views/web_gantt.xml',
    ],
    'qweb': [
        'static/src/xml/*.xml',
    ],
    'auto_install': True
}
