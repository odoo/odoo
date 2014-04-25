{
    'name': 'Gauge Widget for Kanban',
    'category': 'Hidden',
    'description': """
This widget allows to display gauges using justgage library.
""",
    'version': '1.0',
    'depends': ['web_kanban'],
    'js': [
        'static/lib/justgage/justgage.js',
        'static/src/js/kanban_gauge.js'
    ],
    'css': [
    ],
    'qweb': [
    ],
    'auto_install': True,
}
