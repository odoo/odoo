{
    "name" : "OpenERP Web Diagram",
    "category" : "Hidden",
    "description":"""Openerp Web Diagram view.""",
    "version" : "2.0",
    "depends" : ["web"],
    "js": [
        'static/lib/js/raphael.js',
        'static/lib/js/jquery.mousewheel.js',
        'static/src/js/vec2.js',
        'static/src/js/graph.js',
        'static/src/js/diagram.js',
    ],
    'css' : [
        "static/src/css/base_diagram.css",
    ],
    'qweb' : [
        "static/src/xml/*.xml",
    ],
    'auto_install': True,
}
