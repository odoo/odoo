{
    'name': 'Odoo_frisle',
    'version': '1.0',
    'category': 'All',
    'summary': 'Test case for job',
    'description': "Test case for job",
    'website': 'https://www.odoo.com/app/Odoo_frisle',
    'application': True,
    'installable': True,
    'depends': ['sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/frisle_views.xml',
        'views/frisle_menu.xml',
        'views/sale.xml',
        'views/inherit_report_sale.xml'
    ],
    'license': 'LGPL-3'
}