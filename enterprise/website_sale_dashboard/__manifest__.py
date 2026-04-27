{
    'name': 'Website Sales Dashboard',
    'category': 'Hidden',
    'sequence': 55,
    'summary': 'Get a new dashboard view in the Website App',
    'version': '1.0',
    'description': """
This module adds a new dashboard view in the Website application.
This new type of view contains some basic statistics, a graph, and a pivot subview that allow you to get a quick overview of your online sales.
It also provides new tools to analyse your data.
    """,
    'depends': ['website_sale'],
    'data': [
        'views/dashboard_view.xml',
    ],
    'auto_install': ['website_sale'],
    'license': 'OEEL-1',
}
