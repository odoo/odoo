# -*- coding: utf-8 -*-

{
    'name': 'Portal Tests',
    'version': '1.0',
    'category': 'Hidden',
    'sequence': 9877,
    'summary': 'Portal Tests: performances and tests specific to portal + mail',
    'description': """This module contains tests related to portal-enabled models
also using mail.thread. Those are contained in a separate module as it contains models
used only to perform tests independently to functional aspects of other models. """,
    'depends': ['test_mail', 'portal'],
    'data': [
        'security/ir.model.access.csv',
    ],
    'demo': [
        # 'data/demo.xml',
    ],
    'installable': True,
    'application': False,
}
