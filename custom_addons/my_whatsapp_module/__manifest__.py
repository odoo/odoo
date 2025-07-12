{
    'name': 'Send Invoice by WhatsApp',
    'version': '1.0',
    'summary': 'Add Send by WhatsApp button to Invoices',
    'sequence': 10,
    'depends': ['account'],
    'data': [
        'views/account_move_views.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'application': True,
}
