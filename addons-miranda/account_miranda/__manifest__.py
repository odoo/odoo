#-*- coding: utf-8 -*-
{
    'name': "Contabilidad Miranda",
    'summary': """
        Módulo complementario para contabilidad por Miranda Partner
    """,
    'description': """
        Módulo complementario para contabilidad por Miranda Partner
    """,
    'author': "Miranda Partner",
    'website': "",
    'category': 'Account',
    'version': '1.0',
    'depends': [ 
        'account','account_reports','stock','purchase','sale_management',
    ],
    'data': [
        'views/account_inherit.xml'
    ],
    'qweb':[
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}

