# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.controllers.discuss.settings import DiscussSettingsController


class LivechatDiscussSettings(DiscussSettingsController):
    def _get_allowed_push_channel_types(self):
        return super()._get_allowed_push_channel_types() + ["livechat_push"]
