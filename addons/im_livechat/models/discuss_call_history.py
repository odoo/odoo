# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class DiscussCallHistory(models.Model):
    _inherit = "discuss.call.history"
    _explanation = "In the Livechat context, we extend call history to track participants (operators and visitors) involved in the call."

    livechat_participant_history_ids = fields.Many2many("im_livechat.channel.member.history")
