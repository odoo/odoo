{
    "name": "web Gantt",
    "category" : "Hidden",
    "description":'Openerp web gantt chart',
    "version": "2.0",
    "depends": ['web'],
    "js": [
        'static/lib/dhtmlxGantt/sources/dhtmlxcommon.js',
        'static/lib/dhtmlxGantt/sources/dhtmlxgantt.js',
        'static/src/js/gantt.js'
    ],
    "css": ['static/lib/dhtmlxGantt/codebase/dhtmlxgantt.css'],
    'qweb' : [
        "static/src/xml/*.xml",
    ],
    'active': True
}
