# -*- coding: utf-8 -*-

{
    'name': 'Mail Tests',
    'version': '1.0',
    'category': 'Hidden',
    'sequence': 9876,
    'summary': 'Mail Tests: performances and tests specific to mail',
    'description': """This module contains tests related to mail. Those are
contained in a separate module as it contains models used only to perform
tests independently to functional aspects of other models. """,
    'depends': ['test_performance', 'mail', 'mail_bot'],
    'data': [
        'security/ir.model.access.csv',
        'data/data.xml',
    ],
    'demo': [
        'data/demo.xml',
        'data/subtype_demo.xml',
        'data/template_demo.xml',
    ],
    'installable': True,
    'application': False,
}
