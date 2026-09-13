from odoo import fields, models

from odoo.addons.mail.tools.discuss import add_guest_to_context


class Website(models.Model):
    _inherit = "website"

    channel_id = fields.Many2one(
        comodel_name="im_livechat.channel",
        string="Website Live Chat Channel",
    )

    @add_guest_to_context
    def _get_livechat_channel_info(self):
        self.check_singleton()
        if self.channel_id:
            return self.channel_id.sudo().get_livechat_info()
        return {}
