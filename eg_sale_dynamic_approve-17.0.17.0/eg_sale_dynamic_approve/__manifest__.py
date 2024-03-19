{
    'name': 'Sale Dynamic Approve',
    'version': '17.0',
    'category': 'Sales/Sales',
    'summary': 'Sale Order Dynamic Approval Workflow Odoo Apps',
    'author': 'INKERP',
    'website': 'https://www.inkerp.com/',
    'depends': ['base', 'sale', 'sales_team'],
    
    'data': [
        'security/ir.model.access.csv',
        'views/sale_teams_views.xml',
        'views/sale_order_view.xml',
    ],
    
    'images': ['static/description/banner.png'],
    'license': "OPL-1",
    'installable': True,
    'application': True,
    'auto_install': False,
}
