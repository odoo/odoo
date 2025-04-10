# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from odoo.addons.mail.tools.discuss import add_guest_to_context


class Website(models.Model):
    _inherit = "website"

    channel_id = fields.Many2one('im_livechat.channel', string='Website Live Chat Channel')

    @add_guest_to_context
    def _get_livechat_channel_info(self):
        """ Get the livechat info dict (button text, channel name, ...) for the livechat channel of
            the current website.
        """
        self.ensure_one()
        if self.channel_id:
            # sudo - im_livechat.channel: getting bsaic info related to live chat channel is allowed.
            return self.channel_id.sudo().get_livechat_info()
        return {}
