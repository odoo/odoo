{
    'name': 'Gauge Widget for Kanban',
    'category': 'Hidden',
    'description': """
This widget allows to display gauges using justgage library.
""",
    'version': '1.0',
    'depends': ['web_kanban'],
    'data' : [
        'views/web_kanban_gauge.xml',
    ],
    'qweb': [
    ],
    'auto_install': True,
}
