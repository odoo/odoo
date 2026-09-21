from odoo import fields, models


class ScorecardDimension(models.Model):
    _inherit = "scorecard.dimension"

    code = fields.Selection(
        selection_add=[("partner_attr", "Contact Attribute")],
        ondelete={"partner_attr": "cascade"},
    )
