{
    "name": "On Hand Qty on Sale Order",
    "summary": "Display On hand quantity and forecasted qty in sale order line.",
    "version": "16.0.1.0.0",
    "category": "Sales",
    "description": "Display On hand quantity and forecasted qty in sale order line.",
    "author": "INKERP",
    "website": "https://www.INKERP.com",
    "depends": [
        'sale_management',

    ],
    "data": [
        'views/sale_order_line_view.xml',
        'report/sale_order_report.xml'
    ],

    'images': ['static/description/banner.png'],
    'license': "OPL-1",
    'installable': True,
    'auto_install': False,
    'application': True,
}
