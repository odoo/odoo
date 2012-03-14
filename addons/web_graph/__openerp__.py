{
    "name": "web Graph",
    "category" : "Hidden",
    "description":'Openerp web graph view',
    "version": "2.0",
    "depends": ['web'],
    "js": [
        "static/lib/dhtmlxGraph/codebase/thirdparty/excanvas/excanvas.js",
        "static/lib/dhtmlxGraph/codebase/dhtmlxchart.js",
        "static/src/js/graph.js"],
    "css": ["static/lib/dhtmlxGraph/codebase/dhtmlxchart.css"],
    'qweb' : [
        "static/src/xml/*.xml",
    ],
    "auto_install": True
}
