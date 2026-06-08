# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class TestInheritMother(models.Model):
    _inherit = 'test.inherit.mother'

    # extend again the selection of the state field: 'd' must precede 'b'
    state = fields.Selection(selection_add=[('d', 'D'), ('b',)])
    field_in_mother_3 = fields.Char()
