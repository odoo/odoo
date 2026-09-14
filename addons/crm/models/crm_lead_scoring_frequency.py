from odoo import fields, models


class CrmLeadScoringFrequency(models.Model):
    _name = "crm.lead.scoring.frequency"
    _description = "Lead Scoring Frequency"

    variable = fields.Char(index=True)
    value = fields.Char()
    won_count = fields.Float(digits=(16, 1))
    lost_count = fields.Float(digits=(16, 1))
    team_id = fields.Many2one(
        comodel_name="team.team",
        string="Sales Team",
        domain=[("use_sale", "=", True)],
        ondelete="cascade",
    )


class CrmLeadScoringFrequencyField(models.Model):
    _name = "crm.lead.scoring.frequency.field"
    _inherit = ["mixin.color"]
    _description = "Fields that can be used for predictive lead scoring computation"

    name = fields.Char(related="field_id.field_description")
    field_id = fields.Many2one(
        comodel_name="ir.model.fields",
        required=True,
        domain=[("model_id.model", "=", "crm.lead")],
        ondelete="cascade",
    )
    color = fields.Integer(default=lambda self: self._default_color())
