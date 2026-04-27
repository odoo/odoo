# -*- coding: utf-8 -*-

{
    'name': 'Timer Tests',
    'version': '1.0',
    'category': 'Hidden/Tests',
    'sequence': 8765,
    'summary': 'Timer Tests: feature and performance tests for timer',
    'description': """This module contains tests related to timer. Those are
present in a separate module as it contains models used only to perform
tests independently to functional aspects of other models. """,
    'depends': ['timer'],
    'data': [
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'license': 'OEEL-1',
}
