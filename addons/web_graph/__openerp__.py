{
    "name": "Graph Views",
    "category" : "Hidden",
    "description":"""Graph Views for Web Client

* Parse a <graph> view but allows changing dynamically the presentation
* Graph Types: pie, lines, areas, bars, radar
* Stacked/Not Stacked for areas and bars
* Legends: top, inside (top/left), hidden
* Features: download as PNG or CSV, browse data grid, switch orientation
* Unlimited "Group By" levels (not stacked), two cross level analysis (stacked)
""",
    "version": "3.0",
    "depends": ['web'],
    "js": [
        "static/lib/dropdown.js",
        "static/lib/flotr2/lib/bean.js",
        "static/lib/flotr2/js/Flotr.js",
        "static/lib/flotr2/js/DefaultOptions.js",
        "static/lib/flotr2/js/Color.js",
        "static/lib/flotr2/js/Date.js",
        "static/lib/flotr2/js/DOM.js",
        "static/lib/flotr2/js/EventAdapter.js",
        "static/lib/flotr2/js/Text.js",
        "static/lib/flotr2/js/Graph.js",
        "static/lib/flotr2/js/Axis.js",
        "static/lib/flotr2/js/Series.js",
        "static/lib/flotr2/js/types/lines.js",
        "static/lib/flotr2/js/types/bars.js",
        "static/lib/flotr2/js/types/bubbles.js",
        "static/lib/flotr2/js/types/candles.js",
        "static/lib/flotr2/js/types/gantt.js",
        "static/lib/flotr2/js/types/markers.js",
        "static/lib/flotr2/js/types/pie.js",
        "static/lib/flotr2/js/types/points.js",
        "static/lib/flotr2/js/types/radar.js",
        "static/lib/flotr2/js/types/timeline.js",
        "static/lib/flotr2/js/plugins/crosshair.js",
        "static/lib/flotr2/js/plugins/download.js",
        "static/lib/flotr2/js/plugins/grid.js",
        "static/lib/flotr2/js/plugins/hit.js",
        "static/lib/flotr2/js/plugins/selection.js",
        "static/lib/flotr2/js/plugins/labels.js",
        "static/lib/flotr2/js/plugins/legend.js",
        "static/lib/flotr2/js/plugins/spreadsheet.js",
        "static/lib/flotr2/js/plugins/titles.js",
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
