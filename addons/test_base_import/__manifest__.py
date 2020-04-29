{
    'name': 'Base Import - Tests',
    'version': '1.0',
    'category': 'Hidden',
    'sequence': 8765,
    'summary': 'Base Import Tests: feature tests for base_import module',
    'description': """This module contains tests related to base_import. Those
are contained in a separate module to use specific test models. """,
    'depends': ['base_import', 'partner'],
    'data': [
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'application': False,
}
