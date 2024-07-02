# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields
from . import mother_inherit_1


class TestINHERITMother(mother_inherit_1.TestINHERITMother):
    # extend again the selection of the state field: 'd' must precede 'b'
    state = fields.Selection(selection_add=[('d', 'D'), ('b',)])
    field_in_mother_3 = fields.Char()
