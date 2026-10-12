# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _


class DiscussChannel(models.Model):
    _inherit = 'discuss.channel'

    def execute_command_help(self, **kwargs):
        super().execute_command_help(**kwargs)
        self.env['mail.bot']._apply_logic(self, None, command="help")

    def _message_post_after_hook(self, message):
        self.env["mail.bot"]._apply_logic(self, message)
        return super()._message_post_after_hook(message)
