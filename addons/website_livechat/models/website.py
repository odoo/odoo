# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class Website(models.Model):

    _inherit = "website"

    channel_id = fields.Many2one('im_livechat.channel', string='Website Live Chat Channel')

    def get_livechat_channel_info(self):
        """ Get the livechat info dict (button text, channel name, ...) for the livechat channel of
            the current website.
        """
        self.ensure_one()
        if self.channel_id:
            return self.channel_id.sudo().get_livechat_info()
        return {}
