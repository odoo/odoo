# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'test-inherit-depends',
    'version': '1.0',
    'category': 'Hidden/Tests',
    'description': """A module to verify the inheritance using _inherit across modules.""",
    'depends': ['test_inherit', 'test_orm'],
    'installable': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
