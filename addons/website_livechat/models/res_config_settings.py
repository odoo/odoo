from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    channel_id = fields.Many2one(
        comodel_name="im_livechat.channel",
        related="website_id.channel_id",
        string="Website Live Channel",
        readonly=False,
    )
