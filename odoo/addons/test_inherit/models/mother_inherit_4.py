# Part of Odoo. See LICENSE file for full copyright and licensing details.
from . import mother_inherit_2

from odoo import fields


class TestInheritMother(mother_inherit_2.TestInheritMother):

    # extend again the selection of the state field: 'e' must precede 'e'
    state = fields.Selection(selection_add=[('e', 'E')])
    field_in_mother_4 = fields.Char()

    def foo(self):
        return self.bar()
