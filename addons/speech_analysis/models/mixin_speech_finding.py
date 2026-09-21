from odoo import fields, models


class MixinSpeechFinding(models.AbstractModel):
    _name = "mixin.speech.finding"
    _inherit = ["mixin.owner.access"]
    _description = "Speech Finding"
    _access_owner_field = "res_id"
    _order = "res_model, res_id, at_s, id"

    name = fields.Char(required=True)
    res_model = fields.Char(
        string="Resource Model",
        index="btree_not_null",
        required=True,
    )
    res_id = fields.Many2oneReference(
        model_field="res_model",
        string="Resource ID",
        required=True,
    )
    at_s = fields.Float(
        string="At (s)",
        digits=(12, 1),
    )
    speaker_id = fields.Many2one(
        comodel_name="speech.speaker",
        ondelete="set null",
    )
    partner_id = fields.Many2one(related="speaker_id.partner_id")
