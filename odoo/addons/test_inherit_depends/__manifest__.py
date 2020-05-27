# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'test-inherit-depends',
    'version': '0.1',
    'category': 'Hidden/Tests',
    'description': """A module to verify the inheritance using _inherit accross modules.""",
    'depends': ['test_inherit', 'test_inherits'],
    'data': [
        'ir.model.access.csv',
    ],
    'installable': True,
    'auto_install': False,
}
