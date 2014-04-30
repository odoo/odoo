{
    'name': 'Graph Views',
    'category': 'Hidden',
    'description': """
Graph Views for Web Client.
===========================

    * Parse a <graph> view but allows changing dynamically the presentation
    * Graph Types: pie, lines, areas, bars, radar
    * Stacked/Not Stacked for areas and bars
    * Legends: top, inside (top/left), hidden
    * Features: download as PNG or CSV, browse data grid, switch orientation
    * Unlimited "Group By" levels (not stacked), two cross level analysis (stacked)
""",
    'version': '3.0',
    'depends': ['web'],
    'data' : [
        'views/web_graph.xml',
    ],
    'qweb' : [
        'static/src/xml/*.xml',
    ],
    'auto_install': True
}
