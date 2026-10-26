# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

from odoo.addons.mail.tools.discuss import add_guest_to_context


class Website(models.Model):
    _inherit = "website"

    channel_id = fields.Many2one('im_livechat.channel', string='Website Live Chat Channel')

    @api.model_create_multi
    def create(self, vals_list):
        websites = super().create(vals_list)
        websites.filtered("channel_id")._seed_livechat_theme_colors()
        return websites

    def write(self, vals):
        result = super().write(vals)
        if "channel_id" in vals:
            self._seed_livechat_theme_colors()
        return result

    def _seed_livechat_theme_colors(self):
        """Make a newly linked channel follow the website's theme, rather than
        leaving it on im_livechat's generic defaults. Customized colors are
        kept, as well as the colors of a channel following another website."""
        for website in self:
            channel = website.channel_id.sudo()
            if channel and channel._get_website() == website and channel._has_default_colors():
                channel.theme_colors_synced = True
                channel._schedule_theme_colors_sync()

    def _schedule_livechat_theme_colors_sync(self):
        """Called whenever the theme colors of the websites may change. A channel
        shared by several websites only follows the first one."""
        channels = self.env["im_livechat.channel"]
        for website in self:
            channel = website.channel_id.sudo()
            if channel.theme_colors_synced and channel._get_website() == website:
                channels |= channel
        channels._schedule_theme_colors_sync()

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
