# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'test-inherit-inherits-depends',
    'version': '1.0',
    'category': 'Hidden/Tests',
    'description': """A module to verify the inheritance using _inherit and _inherits across modules.""",
    'depends': ['test_inherit', 'test_new_api'],
    'data': [
        'ir.model.access.csv',
    ],
    'installable': True,
    'license': 'LGPL-3',
}
