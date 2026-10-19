# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

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

    @api.model
    def _get_settings_to_copy_onto_new_default_website(self):
        """ Provides a list of settings that should always be set on the default
        website. When the default website changes, a check is performed. If some
        of these settings are not already set on the new default website, they
        are copied from the previous default website."""
        return super()._get_settings_to_copy_onto_new_default_website() + ['channel_id']
