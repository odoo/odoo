{
    "name": "Web Calendar",
    "category": "Hidden",
    "description":"""
OpenERP Web Calendar view.
==========================

""",
    "version": "2.0",
    "depends": ['web'],
    "js": [
        'static/lib/dhtmlxScheduler/codebase/dhtmlxscheduler_debug.js',
        'static/lib/dhtmlxScheduler/sources/ext/ext_minical.js',
        'static/src/js/calendar.js'
    ],
    "css": [
            'static/lib/dhtmlxScheduler/codebase/ext/dhtmlxscheduler_ext.css',
            'static/src/css/web_calendar.css'
            ],
    'qweb' : [
        "static/src/xml/*.xml",
    ],
    'auto_install': True
}
