from odoo import api, fields, models


class TestInheritMother(models.Model):
    _inherit = "test.inherit.mother"

    state = fields.Selection(
        selection_add=[("c", "C")],
        default=None,
    )
    field_in_mother_2 = fields.Char()

    @api.depends("field_in_mother")
    def _compute_surname(self):
        for rec in self:
            if rec.field_in_mother:
                rec.surname = rec.field_in_mother
            else:
                super(TestInheritMother, rec)._compute_surname()
