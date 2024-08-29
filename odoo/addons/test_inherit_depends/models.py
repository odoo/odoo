# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons import test_new_api, test_inherit

from odoo import models, fields
from odoo.addons.test_inherit.models import mother_base


class TestNewApiFoo(models.Model, test_new_api.TestNewApiFoo, test_inherit.TestInheritMixin):
    _name = 'test_new_api.foo'


class TestINHERITMother(mother_base.TestINHERITMother):
    # extend again the selection of the state field: 'e' must precede 'e'
    state = fields.Selection(selection_add=[('g', 'G')])
    field_in_mother_5 = fields.Char()

    def foo(self):
        return super().foo() * 2
