from odoo import fields, models


class PartnerScoreLine(models.Model):
    _name = "partner.score.line"
    _inherit = ["mixin.score.line"]
    _description = "Partner Score Line"
    _order = "subject_id, dimension_id, id"

    subject_id = fields.Many2one(
        comodel_name="res.partner",
        string="Partner",
        index=True,
        required=True,
        ondelete="cascade",
    )
