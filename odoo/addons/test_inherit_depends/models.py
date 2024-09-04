# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields
from odoo.addons.test_inherit.models import mother_base


class TestNewApiFoo(models.Model):
    _name = 'test_new_api.foo'
    _inherit = ['test_new_api.foo', 'test_inherit_mixin']


class TestINHERITMother(mother_base.TestINHERITMother):
    # extend again the selection of the state field: 'e' must precede 'e'
    state = fields.Selection(selection_add=[('g', 'G')])
    field_in_mother_5 = fields.Char()

    def foo(self):
        return super().foo() * 2
