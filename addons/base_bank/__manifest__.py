{
    'name': 'Base bank',  # todo (rugo) - Name ?
    'category': 'Hidden',  # todo (rugo) - Category ?
    'version': '1.0',
    'description': """Base bank""",  # todo (rugo) - Description ?
    'depends': ['base'],
    'data': [
        'data/clearing_label_data.xml',
        'security/ir.model.access.csv',
        'views/clearing_label_views.xml',
        'views/res_partner_bank_views.xml',
    ],
    'demo': [
        'data/res_partner_bank_demo.xml',
    ],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}

