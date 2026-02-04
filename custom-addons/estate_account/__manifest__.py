{
    'name': "Real Estate Accounting",
    'version': '1.0',
    'category': 'Sales/Real Estate',
    'summary': 'Real Estate Property Invoicing',
    'description': """
        Link module for Real Estate and Accounting
        ==========================================
        
        This module links the Real Estate and Accounting modules.
        When a property is sold, it automatically creates an invoice.
    """,
    'license': 'LGPL-3',
    'depends': ['estate', 'account'],
    'data': [
        'views/estate_property_views.xml',
        'report/estate_reports.xml',
    ],
    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': True,
}