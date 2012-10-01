{
    'name': 'Web Gantt',
    'category': 'Hidden',
    'description': """
OpenERP Web Gantt chart view.
=============================

""",
    'version': '2.0',
    'depends': ['web'],
    'js': [
        'static/lib/dhtmlxGantt/sources/dhtmlxcommon.js',
        'static/lib/dhtmlxGantt/sources/dhtmlxgantt.js',
        'static/src/js/gantt.js'
    ],
    'css': ['static/src/css/gantt.css', 'static/lib/dhtmlxGantt/codebase/dhtmlxgantt.css'],
    'qweb': [
        'static/src/xml/*.xml',
    ],
    'auto_install': True
}
