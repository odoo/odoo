{
    "name": "web Graph",
    "category" : "Hidden",
    "version": "2.0",
    "depends": ['web'],
    "js": [
           "static/lib/dhtmlxGraph/codebase/dhtmlxchart_debug.js",
           "static/src/js/graph.js"],
    "css": ["static/lib/dhtmlxGraph/codebase/dhtmlxchart.css"],
    'qweb' : [
        "static/src/xml/*.xml",
    ],
    "active": True
}
