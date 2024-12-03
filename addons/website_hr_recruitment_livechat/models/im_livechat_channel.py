# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class ImLivechatChannelRule(models.Model):
    _inherit = 'im_livechat.channel.rule'

    is_script_flexible = fields.Boolean(default=False)
