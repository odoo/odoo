{
    'name': 'Test Lint',
    'version': '0.1',
    'category': 'Hidden/Tests',
    'description': """A module to test Odoo code with various linters.""",
    'depends': ['base'],
    'external_dependencies': [
        {'pypi': 'pylint', 'test': True},
    ],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
