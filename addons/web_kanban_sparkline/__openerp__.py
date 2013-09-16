{
    'name': 'Sparkline Widget for Kanban',
    'category': 'Hidden',
    'description': """
This widget allows to display sparklines using jquery.sparkline library.
""",
    'version': '1.0',
    'depends': ['web_kanban'],
    'js': [
        "static/lib/jquery.sparkline/jquery.sparkline.js",
        'static/src/js/kanban_sparkline.js'
    ],
    'css': [
    ],
    'qweb': [
    ],
    'auto_install': False,
}
