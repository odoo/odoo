# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons import test_inherit

from odoo import models, fields


class TestINHERITMother(models.Model, test_inherit.TestINHERITMother):

    # extend again the selection of the state field: 'e' must precede 'e'
    state = fields.Selection(selection_add=[('e', 'E')])
    field_in_mother_4 = fields.Char()

    def foo(self):
        return self.bar()
