{
    'name': 'Advance Payment in Sale Order',
    'version': '16.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Advance Payment in Sale Order',
    'author': 'INKERP',
    'website': 'https://www.INKERP.com/',
    'depends': ['account', 'sale_management'],

    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'wizard/advance_payment_wizard_view.xml',
        'views/sale_order_view.xml',
    ],

    'images': ['static/description/banner.png'],
    'license': "OPL-1",
    'installable': True,
    'application': True,
    'auto_install': False,
}
