# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields
from . import mother_inherit_2, mother_inherit_3


class TestINHERITMother(mother_inherit_2.TestINHERITMother, mother_inherit_3.TestINHERITMother):
    # extend again the selection of the state field: 'e' must precede 'e'
    state = fields.Selection(selection_add=[('e', 'E')])
    field_in_mother_4 = fields.Char()

    def foo(self):
        return self.bar()
