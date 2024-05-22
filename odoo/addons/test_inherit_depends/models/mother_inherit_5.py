# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields
from odoo.addons.test_inherit.models import mother_inherit_4


class TestINHERITMother(mother_inherit_4.TestINHERITMother):
    # extend again the selection of the state field: 'e' must precede 'e'
    state = fields.Selection(selection_add=[('g', 'G')])
    field_in_mother_5 = fields.Char()

    def foo(self):
        return super().foo() * 2
