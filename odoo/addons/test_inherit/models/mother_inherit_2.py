# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api, fields


class TestInheritMother(models.Model):
    _inherit = 'test.inherit.mother'

    # extend the selection of the state field, and discard its default value
    state = fields.Selection(selection_add=[('c', 'C')], default=None)
    field_in_mother_2 = fields.Char()

    # override the computed field, and extend its dependencies
    @api.depends('field_in_mother')
    def _compute_surname(self):
        for rec in self:
            if rec.field_in_mother:
                rec.surname = rec.field_in_mother
            else:
                super(TestInheritMother, rec)._compute_surname()
