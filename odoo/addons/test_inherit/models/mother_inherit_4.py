# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class TestInheritMother(models.Model):
    _inherit = 'test.inherit.mother'

    # extend again the selection of the state field: 'e' must precede 'e'
    state = fields.Selection(selection_add=[('e', 'E')])
    field_in_mother_4 = fields.Char()

    def foo(self):
        return self.bar()
