{
    'name': 'Web Calendar',
    'category': 'Hidden',
    'description':"""
OpenERP Web Calendar view.
==========================

""",
    'author': 'OpenERP SA, Valentino Lab (Kalysto)',
    'version': '2.0',
    'depends': ['web'],
    'data' : [],
    'js': [
        'static/lib/fullcalendar/js/fullcalendar.js',
        'static/src/js/*.js'
    ],
    'css': [
        'static/lib/fullcalendar/css/*.css',
        'static/src/css/*.css'
    ],
    'qweb': [
        'static/src/xml/*.xml',
    ],
    'auto_install': True
}
