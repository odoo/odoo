{
    "name": "Graph Views",
    "category" : "Hidden",
    "description":"""Graph Views for Web Client

* Parse a <graph> view but allows changing dynamically the presentation
* Graph Types: pie, lines, areas, bars, radar
* Stacked / Not Stacked for areas and bars
* Legends: top, inside (top/left), hidden
* Features: download as PNG or CSV, browse data grid, switch orientation
* Unlimited "Group By" levels, multi level analysis
""",
    "version": "3.0",
    "depends": ['web'],
    "js": [
        "static/lib/flotr2/flotr2.js",
        "static/src/js/graph.js"
    ],
    "css": [
        "static/src/css/*.css",
    ],
    'qweb' : [
        "static/src/xml/*.xml",
    ],
    "auto_install": True
}
