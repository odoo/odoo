{
    "name": "web calendar",
    "category" : "Hidden",
    "version": "2.0",
    "depends": ['web'],
    "js": [
        'static/lib/dhtmlxScheduler/codebase/dhtmlxscheduler_debug.js',
        'static/lib/dhtmlxScheduler/codebase/ext/dhtmlxscheduler_minical.js',
        'static/src/js/calendar.js'
    ],
    "css": ['static/lib/dhtmlxScheduler/codebase/dhtmlxscheduler.css',
            'static/lib/dhtmlxScheduler/codebase/ext/dhtmlxscheduler_ext.css'
            ],
    'qweb' : [
        "static/src/xml/*.xml",
    ],
    'active': True
}
