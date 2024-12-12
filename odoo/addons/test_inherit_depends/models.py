# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class Test_New_ApiFoo(models.Model):
    _name = 'test_new_api.foo'
    _inherit = ['test_new_api.foo', 'test_inherit_mixin']


class TestInheritMother(models.Model):
    _inherit = 'test.inherit.mother'

    # extend again the selection of the state field: 'e' must precede 'e'
    state = fields.Selection(selection_add=[('g', 'G')])
    field_in_mother_5 = fields.Char()

    def foo(self):
        return super().foo() * 2
