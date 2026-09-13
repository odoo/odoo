from odoo import fields, models


class DiscussCallHistory(models.Model):
    _inherit = "discuss.call.history"

    livechat_participant_history_ids = fields.Many2many(
        comodel_name="im_livechat.channel.member.history"
    )
