{
    'name': 'Stock Transport Enterprise',
    'summary': 'Bridge module for stock_fleet and enterprise',
    'version': '1.0',
    'description': """
    Bridge module for stock_fleet and enterprise""",
    'depends': ['stock_fleet', 'web_gantt', 'web_map'],
    'auto_install': True,
    'license': 'OEEL-1',
    'data': [
        "views/batch_gantt.xml",
        "views/stock_picking_view.xml",
        "views/stock_picking_batch.xml",
    ],
}
