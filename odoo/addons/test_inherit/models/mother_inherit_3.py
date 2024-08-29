# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons import test_inherit

from odoo import models, fields


class TestINHERITMother(models.Model, test_inherit.TestINHERITMother):

    # extend again the selection of the state field: 'd' must precede 'b'
    state = fields.Selection(selection_add=[('d', 'D'), ('b',)])
    field_in_mother_3 = fields.Char()
