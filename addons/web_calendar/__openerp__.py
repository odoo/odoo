{
    'name': 'Web Calendar',
    'category': 'Hidden',
    'description':"""
Calendar view client
====================

""",
    'author': 'OpenERP SA, Valentino Lab (Kalysto)',
    'version': '2.0',
    'depends': ['web'],
    'data' : [
        'views/web_calendar.xml',
    ],
    'qweb': [
        'static/src/xml/*.xml',
    ],
    'auto_install': True
}
