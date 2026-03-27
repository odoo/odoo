{
    'name': "Add Partner GLN",
    'summary': "This module adds the Global Location Number to the partner. Used on delivery addresses, it is used to identify stock locations and is mandatory on the UBL/CII eInvoices (but not only). The module is intended be merged with account, later on, in master",
    'category': 'Accounting/Accounting',
    'version': '1.0',
    'depends': ['account'],
    'installable': True,
    'auto_install': True,
    'data': [
        'views/res_partner_views.xml',
    ],
    'license': 'LGPL-3',
}
