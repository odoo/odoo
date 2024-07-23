{
    'name': 'Test - Import & Export',
    'version': '1.0',
    'category': 'Hidden',
    'sequence': 3843,
    'summary': 'Base Import & Export Tests: Ensure Flow Robustness',
    'description': """This module contains tests related to base import and export.""",
    'depends': ['web', 'base_import'],
    'data': [
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'license': 'LGPL-3',
}
