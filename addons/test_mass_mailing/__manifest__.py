# -*- coding: utf-8 -*-

{
    'name': 'Mass Mail Tests',
    'version': '1.0',
    'category': 'Hidden',
    'sequence': 8765,
    'summary': 'Mass Mail Tests: feature and performance tests for mass mailing',
    'description': """This module contains tests related to mass mailing. Those
are present in a separate module to use specific test models defined in
test_mail. """,
    'depends': ['test_mail', 'mass_mailing'],
    'data': [
        'security/ir.model.access.csv',
    ],
    'demo': [
    ],
    'installable': True,
    'application': False,
}
